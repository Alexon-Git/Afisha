"""PostgreSQL queue worker. Start: python -m app.imports.worker.

Every persisted record and terminal transition checks the current lease token.
Network happens outside transactions; expired workers cannot commit observations.
"""
from datetime import datetime, timedelta, timezone
import signal
import threading
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from uuid import uuid4

from sqlalchemy import or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from ..models import ImportSource, ImportRun
from .dedup import store_record
from .fetcher import SafeFetcher, USER_AGENT
from .jsonld import extract
from .policy import ImportFailure, check_policy, check_url

LEASE_SECONDS=45
MAX_ATTEMPTS=3


def now():
    return datetime.now(timezone.utc)


def claim(sessions):
    with sessions.begin() as db:
        # Source row locks serialize claims for a source without serializing all workers.
        sources=list(db.scalars(select(ImportSource)
            .order_by(ImportSource.id).with_for_update(skip_locked=True)))
        for source in sources:
            running=db.scalar(select(ImportRun).where(ImportRun.source_id==source.id,ImportRun.status=='running').with_for_update())
            if running:
                if running.lease_expires_at and running.lease_expires_at>now():
                    continue
                running.status='interrupted'
                running.error_code='lease_expired'
                running.finished_at=now()
                if running.attempt_count<MAX_ATTEMPTS:
                    running.status='queued'
                running.lease_token=None
                db.flush()
            run=db.scalar(select(ImportRun).where(ImportRun.source_id==source.id,ImportRun.status=='queued',
                or_(ImportRun.lease_expires_at.is_(None),ImportRun.lease_expires_at<=now()))
                .order_by(ImportRun.created_at,ImportRun.id).with_for_update(skip_locked=True).limit(1))
            if not run:
                continue
            try:
                check_policy(source)
                if run.policy_version!=source.policy_version:
                    raise ImportFailure('source_policy_changed',blocked=True)
            except ImportFailure as exc:
                run.status='blocked'
                run.error_code=exc.code
                run.finished_at=now()
                continue
            run.status='running'
            run.attempt_count+=1
            run.lease_token=uuid4()
            run.lease_expires_at=now()+timedelta(seconds=LEASE_SECONDS)
            run.heartbeat_at=run.started_at=now()
            run.finished_at=None
            db.flush()
            return run.id,run.lease_token
    return None


def leased(db,run_id,token):
    source_id=db.scalar(select(ImportRun.source_id).where(ImportRun.id==run_id))
    if source_id is None:
        raise ImportFailure('lease_lost')
    db.scalar(select(ImportSource).where(ImportSource.id==source_id).with_for_update())
    run=db.scalar(select(ImportRun).where(ImportRun.id==run_id).with_for_update()
                  .execution_options(populate_existing=True))
    if not run or run.status!='running' or run.lease_token!=token or not run.lease_expires_at or run.lease_expires_at<=now():
        raise ImportFailure('lease_lost')
    run.heartbeat_at=now()
    run.lease_expires_at=now()+timedelta(seconds=LEASE_SECONDS)
    return run


def policy_for_run(db,run):
    source=db.scalar(select(ImportSource).where(ImportSource.id==run.source_id).with_for_update()
                     .execution_options(populate_existing=True))
    check_policy(source)
    if source.policy_version!=run.policy_version:
        raise ImportFailure('source_policy_changed',blocked=True)
    return source


def before_request(sessions,run_id,token,stop):
    # Reserve a request slot under a DB lock, heartbeat while waiting, revalidate
    # permissions immediately before the actual request. No locks while sleeping.
    while True:
        if stop.is_set():
            raise ImportFailure('shutdown')
        with sessions.begin() as db:
            run=leased(db,run_id,token)
            source=policy_for_run(db,run)
            delay=max(0,(source.next_request_at-now()).total_seconds()) if source.next_request_at else 0
            if delay<=0:
                if run.request_count>=24:  # Total budget across all three attempts.
                    raise ImportFailure('request_budget')
                source.next_request_at=now()+timedelta(seconds=source.request_interval_seconds)
                run.request_count+=1
                return
        stop.wait(min(delay,5))


def finish(sessions,run_id,token,*,error=None,fetcher=None):
    with sessions.begin() as db:
        run=leased(db,run_id,token)
        run.bytes_received+=fetcher.bytes if fetcher else 0
        run.lease_token=None
        run.lease_expires_at=None
        run.finished_at=now()
        if error:
            run.error_code=error.code
            run.error_summary=error.code  # Never persist exception text/URL/body.
            run.record_errors=(run.record_errors+[{'code':error.code,'attempt':run.attempt_count}])[-30:]
            run.status='blocked' if error.blocked else ('interrupted' if error.code=='shutdown' else 'failed')
            if error.code in {'network_failure','dns_failure','response_deadline'} and run.attempt_count<MAX_ATTEMPTS:
                run.status='queued'
                run.lease_expires_at=now()+timedelta(seconds=30*run.attempt_count)
            if error.code in {'http_403','http_429','robots_disallowed'}:
                source=db.get(ImportSource,run.source_id)
                source.state='paused'
        else:
            run.status='partial' if run.records_rejected else 'succeeded'
            run.error_code=run.error_summary=None


def process(sessions,claim_info,stop=None,fetcher_factory=SafeFetcher):
    run_id,token=claim_info
    stop=stop or threading.Event()
    fetcher=None
    try:
        with sessions.begin() as db:
            run=leased(db,run_id,token)
            source=policy_for_run(db,run)
            url=check_url(source,run.requested_url)
            db.expunge(source)
        fetcher=fetcher_factory(source,lambda:before_request(sessions,run_id,token,stop))
        # Fresh robots for every run, never trust an old boolean for arbitrary paths.
        u=urlsplit(url)
        robots_url=f'{u.scheme}://{u.netloc}/robots.txt'
        _,_,body=fetcher.get(robots_url,robots=True)
        if len(body)>65536:
            raise ImportFailure('robots_too_large',blocked=True)
        try:
            rules=body.decode('utf-8')
        except UnicodeError:
            raise ImportFailure('invalid_robots',blocked=True) from None
        # Missing/HTML/empty robots fails closed. Explicit Allow/Disallow required.
        if not any(line.lower().strip().startswith(('allow:','disallow:')) for line in rules.splitlines()):
            raise ImportFailure('invalid_robots',blocked=True)
        robots=RobotFileParser()
        robots.parse(rules.splitlines())
        delay=robots.crawl_delay(USER_AGENT) or 0
        rate=robots.request_rate(USER_AGENT)
        delay=max(delay, rate.seconds/rate.requests if rate and rate.requests else 0)
        if delay>3600:
            raise ImportFailure('robots_rate_requires_review',blocked=True)
        if delay:
            with sessions.begin() as db:
                run=leased(db,run_id,token)
                current=policy_for_run(db,run)
                current.next_request_at=max(current.next_request_at or now(),now()+timedelta(seconds=delay))
        allowed=lambda value:robots.can_fetch(USER_AGENT,value)
        final,headers,body=fetcher.get(url,allowed=allowed)
        records=extract(body,headers.get('content-type',''),final)
        for record in records:
            if stop.is_set():
                raise ImportFailure('shutdown')
            with sessions.begin() as db:
                if db.bind.dialect.name=='postgresql':
                    db.execute(text('SELECT pg_advisory_xact_lock(14414002)'))
                run=leased(db,run_id,token)
                policy_for_run(db,run)
                result=store_record(db,run,record,url)
                run.records_seen+=1
                if result=='created':
                    run.candidates_created+=1
                elif result=='unchanged':
                    run.candidates_unchanged+=1
                run.canonical_url=url
                run.final_url=final
        finish(sessions,run_id,token,fetcher=fetcher)
    except ImportFailure as exc:
        if exc.code!='lease_lost':
            try:
                finish(sessions,run_id,token,error=exc,fetcher=fetcher)
            except ImportFailure:
                pass
    except SQLAlchemyError:
        # No exception text logged; lease recovery retries after expiry. Previously
        # committed candidates survive, current record rolls back automatically.
        return


def main():
    from ..database import SessionLocal, engine
    if engine.dialect.name!='postgresql':
        raise SystemExit('Import worker requires PostgreSQL')
    stop=threading.Event()
    for signum in (signal.SIGTERM,signal.SIGINT):
        signal.signal(signum,lambda *_:stop.set())
    while not stop.is_set():
        try:
            task=claim(SessionLocal)
            if task:
                process(SessionLocal,task,stop)
            else:
                stop.wait(2)
        except SQLAlchemyError:
            stop.wait(5)


if __name__=='__main__':
    main()
