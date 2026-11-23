from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
import json
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.auth.auth import create_access_token
from app.models import Event, EventCandidate, ImportRun, ImportSource, CandidateMatch
from app.imports.actions import transfer
from app.imports.dedup import store_record, refresh_matches
from app.imports.jsonld import extract
from app.imports.worker import claim, process, leased, now
from app.imports.policy import ImportFailure
from app.schemas.import_review import ReviewInput
from test_import_schema import import_database
from test_import_review_api import review_api, APPROVE, BASE

URL='https://example.invalid/101/event'
FACTS={'@type':'Event','@id':URL,'name':'Business meeting','startDate':'2026-11-23T18:00:00+07:00',
 'location':{'name':'Hall','address':{'addressLocality':'Новосибирск'}},'url':URL,
 'description':'COPYRIGHT DO NOT COPY','image':'https://example.invalid/private.jpg','offers':{'price':'0','priceCurrency':'RUB'}}
BODY=json.dumps(FACTS).encode()

@pytest.fixture
def complete_api(review_api):
    client,sessions,runs=review_api
    with sessions.begin() as db:
        source=db.get(ImportSource,101)
        for k,v in dict(state='enabled',access_method='jsonld_html',permission_basis='written_permission',
            permission_reference='fixture-only',terms_url='https://example.invalid/terms',terms_checked_by=1,
            terms_checked_at=now()-timedelta(days=1),review_due_at=now()+timedelta(days=1),
            allowed_origins=['https://example.invalid'],allowed_path_prefixes=['/101'],request_interval_seconds=1).items(): setattr(source,k,v)
        existing=db.get(Event,1); existing.source=None; existing.event_url=None
        c=db.get(EventCandidate,101); c.source_url=c.canonical_source_url=URL; c.venue_name='Hall'; c.city='Новосибирск'; c.normalized_city='новосибирск'
        if db.bind.dialect.name=='postgresql':
            db.execute(text("SELECT setval(pg_get_serial_sequence('events','id'),(SELECT max(id) FROM events))"))
    yield client,sessions,runs
    with sessions.begin() as db:
        for e in db.scalars(select(Event).where(Event.id!=1)): db.delete(e)


def approve(client,cid=101,body=None):
    r=client.post(f'{BASE}/{cid}/approve',json=body or APPROVE)
    assert r.status_code==200,r.text


def test_promote_draft_repeat_invisible(complete_api):
    client,sessions,_=complete_api; approve(client)
    r=client.post(BASE+'/101/promote',json={'expected_revision':1}); assert r.status_code==200,r.text
    eid=r.json()['linked_event_id']
    assert r.json()['review_status']=='converted' and r.json()['link_kind']=='created'
    assert client.post(BASE+'/101/promote',json={'expected_revision':1}).json()['linked_event_id']==eid
    with sessions() as db:
        e=db.get(Event,eid)
        assert e.publication_status=='draft' and e.verified_at is None and e.image_url is None and e.source==URL
        assert db.query(Event).count()==2
    assert client.get('/events/'+str(eid)).status_code==404


def test_link_existing_untouched_repeat(complete_api):
    client,sessions,_=complete_api
    with sessions() as db: before=dict(db.execute(select(Event.__table__).where(Event.id==1)).mappings().one())
    approve(client)
    for _ in range(2): assert client.post(BASE+'/101/link',json={'expected_revision':1,'event_id':1}).status_code==200
    assert client.post(BASE+'/101/promote',json={'expected_revision':1}).status_code==409
    assert client.post(BASE+'/101/link',json={'expected_revision':1,'event_id':2}).status_code==409
    with sessions() as db: assert dict(db.execute(select(Event.__table__).where(Event.id==1)).mappings().one())==before


@pytest.mark.parametrize('mutation,code',[('revision',409),('fingerprint',409),('url',422),('time',422),('location',422),('match',409)])
def test_conversion_fail_closed(complete_api,mutation,code):
    client,sessions,_=complete_api; approve(client)
    with sessions.begin() as db:
        c=db.get(EventCandidate,101)
        if mutation=='revision': c.revision=2
        if mutation=='fingerprint': c.content_fingerprint='e'*64
        if mutation=='url': c.source_url='file:///etc/passwd'
        if mutation=='time': c.time_resolution='ambiguous'
        if mutation=='location': c.venue_name=None
        if mutation=='match': db.get(Event,1).source=URL
    r=client.post(BASE+'/101/promote',json={'expected_revision':1}); assert r.status_code==code,r.text
    with sessions() as db: assert db.query(Event).count()==1 and db.get(EventCandidate,101).linked_event_id is None


def test_deferred_match_requires_editor(complete_api):
    client,sessions,_=complete_api
    with sessions.begin() as db:
        db.get(Event,1).source=URL; refresh_matches(db,db.get(EventCandidate,101))
        mid=db.scalar(select(CandidateMatch).where(CandidateMatch.candidate_id==101)).id
    approve(client,body={**APPROVE,'match_decisions':[{'match_id':mid,'decision':'defer'}]})
    assert client.post(BASE+'/101/promote',json={'expected_revision':1}).status_code==409
    assert client.post(BASE+'/101/link',json={'expected_revision':1,'event_id':1}).status_code==200


def test_edit_invalidates_and_forbids_naive_audit(complete_api):
    client,_,_=complete_api; approve(client)
    for body in [{'start_at':'2026-11-23T12:00:00'},{'review_status':'approved'},{'verified_at':'2026-11-23T12:00:00Z'}]:
        assert client.patch(BASE+'/101',json={'expected_revision':1,**body}).status_code==422
    r=client.patch(BASE+'/101',json={'expected_revision':1,'start_at':'2026-11-24T18:00:00+07:00','city':'Новосибирск'})
    assert r.status_code==200,r.text
    assert r.json()['revision']==2 and r.json()['review_status']=='needs_review' and r.json()['time_resolution']=='manual_confirmed'


ENDPOINTS=[('get','/admin/import/sources',None),('get','/admin/import/runs',None),
 ('get','/admin/import/runs/00000000-0000-0000-0000-000000000000',None),('post','/admin/import/runs',{'source_id':101,'url':URL}),
 ('post',BASE+'/101/promote',{'expected_revision':1}),('post',BASE+'/101/link',{'expected_revision':1,'event_id':1}),
 ('patch',BASE+'/101',{'expected_revision':1,'city':'NSK'}),('post',BASE+'/101/recheck',{})]
@pytest.mark.parametrize('method,url,body',ENDPOINTS)
@pytest.mark.parametrize('identity,code',[(None,403),('ordinary',403),('bad',401)])
def test_auth(complete_api,method,url,body,identity,code):
    token='' if identity is None else 'Bearer '+('invalid' if identity=='bad' else create_access_token({'sub':identity,'is_admin':True}))
    assert complete_api[0].request(method,url,json=body,headers={'Authorization':token,'Idempotency-Key':'auth-test'}).status_code==code


def enqueue(client,key='fixture-key'):
    return client.post('/admin/import/runs',json={'source_id':101,'url':URL},headers={'Idempotency-Key':key})


def test_run_idempotency_permissions_input(complete_api):
    client,sessions,_=complete_api
    first=enqueue(client); assert first.status_code==202,first.text
    assert enqueue(client).json()['id']==first.json()['id']
    assert client.post('/admin/import/runs',json={'source_id':101,'url':URL+'2'},headers={'Idempotency-Key':'fixture-key'}).status_code==409
    for field in ['status','lease_token','policy_version','requested_by','permission_basis']:
        assert client.post('/admin/import/runs',json={'source_id':101,'url':URL,field:'forged'},headers={'Idempotency-Key':'new'}).status_code==422
    for field,value in [('state','paused'),('review_due_at',now()-timedelta(days=1)),('permission_basis',None)]:
        with sessions.begin() as db: source=db.get(ImportSource,101); old=getattr(source,field); setattr(source,field,value)
        assert enqueue(client,'blocked-key').status_code==422
        with sessions.begin() as db: setattr(db.get(ImportSource,101),field,old)
    assert client.get('/admin/import/sources?limit=101').status_code==422
    assert client.get('/admin/import/runs?limit=101').status_code==422
    assert client.get('/admin/import/runs/'+first.json()['id']).status_code==200


class FixtureFetcher:
    def __init__(self,source,before): self.before=before; self.bytes=0
    def get(self,url,**kwargs):
        self.before()
        if kwargs.get('robots'): return url,{},b'User-agent: *\nAllow: /101/\n'
        if kwargs.get('allowed'): assert kwargs['allowed'](url)
        self.bytes=len(BODY)
        return url,{'content-type':'application/ld+json'},BODY


def test_worker_e2e_reimport_revision(complete_api):
    client,sessions,_=complete_api
    with sessions.begin() as db:
        for run in db.scalars(select(ImportRun)): run.status='succeeded'
    assert enqueue(client,'one').status_code==202
    task=claim(sessions); process(sessions,task,fetcher_factory=FixtureFetcher)
    with sessions() as db:
        assert db.get(ImportRun,task[0]).status=='succeeded'
        c=db.scalar(select(EventCandidate).where(EventCandidate.source_item_key==extract(BODY,'application/ld+json',URL)[0]['source_item_key']))
        cid=c.id; assert c.price_amount==0 and c.start_at.hour==11 and c.review_status=='pending'
        assert 'COPYRIGHT' not in str(c.observed_payload) and 'private.jpg' not in str(c.observed_payload)
    approve(client,cid); enqueue(client,'two'); process(sessions,claim(sessions),fetcher_factory=FixtureFetcher)
    with sessions.begin() as db:
        c=db.get(EventCandidate,cid); assert c.revision==1 and c.review_status=='approved'
        record=extract(json.dumps({**FACTS,'name':'Changed'}).encode(),'application/ld+json',URL)[0]
        assert store_record(db,db.get(ImportRun,task[0]),record,URL)=='updated'
        assert c.revision==2 and c.review_status=='needs_review' and c.reviewed_payload['revision']==1


def test_lease_fencing_recovery_and_retry_limit(complete_api):
    _,sessions,_=complete_api; task=claim(sessions); assert task
    with sessions.begin() as db: db.get(ImportRun,task[0]).lease_expires_at=now()-timedelta(seconds=1)
    newer=claim(sessions); assert newer[0]==task[0] and newer[1]!=task[1]
    with pytest.raises(ImportFailure),sessions.begin() as db: leased(db,*task)
    with sessions.begin() as db:
        r=db.get(ImportRun,task[0]); r.lease_expires_at=now()-timedelta(seconds=1); r.attempt_count=3
    claim(sessions)
    with sessions() as db: assert db.get(ImportRun,task[0]).status=='interrupted'


def test_postgresql_workers_and_concurrent_promote(complete_api,import_database):
    if import_database.dialect.name!='postgresql': pytest.skip('PostgreSQL row locks')
    client,sessions,_=complete_api; barrier=Barrier(2)
    def take(_): barrier.wait(timeout=10); return claim(sessions)
    with ThreadPoolExecutor(2) as pool: tasks=list(pool.map(take,range(2)))
    assert sum(t is not None for t in tasks)==1
    approve(client); barrier=Barrier(2)
    def promote(_):
        barrier.wait(timeout=10)
        with sessions() as db: return transfer(db,101,ReviewInput(expected_revision=1),1,'created').linked_event_id
    with ThreadPoolExecutor(2) as pool: ids=list(pool.map(promote,range(2)))
    assert ids[0]==ids[1]
    with sessions() as db: assert db.query(Event).count()==2


def test_db_provenance(complete_api):
    _,sessions,runs=complete_api
    for values in [{'first_run_id':runs[1]},{'last_run_id':runs[1]},{'source_id':102}]:
        with pytest.raises(IntegrityError),sessions.begin() as db: db.execute(EventCandidate.__table__.update().where(EventCandidate.id==101).values(**values))
    with pytest.raises(IntegrityError),sessions.begin() as db: db.execute(ImportRun.__table__.update().where(ImportRun.id==runs[0]).values(source_id=102))


def test_commit_failure_leaves_no_event_or_link(complete_api,monkeypatch):
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import OperationalError
    client,sessions,_=complete_api; approve(client)
    def fail(_): raise OperationalError('sensitive SQL',{},Exception('secret'))
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',fail)
        r=client.post(BASE+'/101/promote',json={'expected_revision':1})
    assert r.status_code==503 and 'secret' not in r.text
    with sessions() as db:
        assert db.query(Event).count()==1
        assert db.get(EventCandidate,101).review_status=='approved' and db.get(EventCandidate,101).linked_event_id is None


def test_worker_crash_preserves_committed_record_then_recovers(complete_api,monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app.imports import worker
    client,sessions,_=complete_api
    with sessions.begin() as db:
        for r in db.scalars(select(ImportRun)): r.status='succeeded'
    enqueue(client,'crash-run');task=claim(sessions)
    records=extract(BODY,'application/ld+json',URL)
    second=extract(json.dumps({**FACTS,'@id':URL+'/two'}).encode(),'application/ld+json',URL)[0]
    original=worker.store_record
    def crash(db,run,record,url):
        if record['source_item_key']==second['source_item_key']:
            raise OperationalError('synthetic crash',{},Exception())
        return original(db,run,record,url)
    with monkeypatch.context() as patch:
        patch.setattr(worker,'extract',lambda *a:records+[second]);patch.setattr(worker,'store_record',crash)
        process(sessions,task,fetcher_factory=FixtureFetcher)
    with sessions.begin() as db:
        assert db.scalar(select(EventCandidate).where(EventCandidate.source_item_key==records[0]['source_item_key'])) is not None
        assert db.scalar(select(EventCandidate).where(EventCandidate.source_item_key==second['source_item_key'])) is None
        run=db.get(ImportRun,task[0]); assert run.status=='running';run.lease_expires_at=now()-timedelta(seconds=1)
    new=claim(sessions);process(sessions,new,fetcher_factory=FixtureFetcher)
    with sessions() as db: assert db.get(ImportRun,task[0]).status=='succeeded'


def test_source_revoked_between_fetch_and_persist(complete_api):
    client,sessions,_=complete_api
    with sessions.begin() as db:
        for r in db.scalars(select(ImportRun)): r.status='succeeded'
    enqueue(client,'revoked-run');task=claim(sessions)
    class Revoked(FixtureFetcher):
        def get(self,url,**kwargs):
            result=super().get(url,**kwargs)
            if not kwargs.get('robots'):
                with sessions.begin() as db: db.get(ImportSource,101).state='prohibited'
            return result
    process(sessions,task,fetcher_factory=Revoked)
    with sessions() as db:
        assert db.get(ImportRun,task[0]).status=='blocked'
        assert db.scalar(select(EventCandidate).where(EventCandidate.source_item_key==extract(BODY,'application/ld+json',URL)[0]['source_item_key'])) is None


def test_worker_shutdown_and_http_pause(complete_api):
    import threading
    client,sessions,_=complete_api
    with sessions.begin() as db:
        for r in db.scalars(select(ImportRun)): r.status='succeeded'
    enqueue(client,'shutdown-run');task=claim(sessions);stop=threading.Event();stop.set()
    process(sessions,task,stop=stop,fetcher_factory=FixtureFetcher)
    with sessions() as db: assert db.get(ImportRun,task[0]).status=='interrupted'
    enqueue(client,'forbidden-run');task=claim(sessions)
    class Forbidden(FixtureFetcher):
        def get(self,*a,**k): raise ImportFailure('http_429',blocked=True)
    process(sessions,task,fetcher_factory=Forbidden)
    with sessions() as db: assert db.get(ImportSource,101).state=='paused' and db.get(ImportRun,task[0]).status=='blocked'


def test_postgresql_concurrent_provenance_writers(complete_api,import_database):
    if import_database.dialect.name!='postgresql': pytest.skip('PG concurrent FK writers')
    _,sessions,runs=complete_api;barrier=Barrier(2)
    def write(kind):
        barrier.wait(timeout=10)
        with pytest.raises(IntegrityError),sessions.begin() as db:
            if kind==0: db.execute(ImportRun.__table__.update().where(ImportRun.id==runs[0]).values(source_id=102))
            else: db.execute(EventCandidate.__table__.update().where(EventCandidate.id==101).values(last_run_id=runs[1]))
    with ThreadPoolExecutor(2) as pool: list(pool.map(write,range(2)))
    with sessions() as db:
        c=db.get(EventCandidate,101)
        assert c.source_id==db.get(ImportRun,c.first_run_id).source_id==db.get(ImportRun,c.last_run_id).source_id


def test_expired_running_on_revoked_source_is_recovered(complete_api):
    _,sessions,_=complete_api;task=claim(sessions);assert task
    with sessions.begin() as db:
        db.get(ImportRun,task[0]).lease_expires_at=now()-timedelta(seconds=1)
        db.get(ImportSource,101).state='prohibited'
    assert claim(sessions) is None
    with sessions() as db: assert db.get(ImportRun,task[0]).status=='blocked'


def test_lease_lost_during_http_cannot_write_or_finish_new_lease(complete_api):
    from app.imports.fetcher import SafeFetcher
    client,sessions,_=complete_api
    with sessions.begin() as db:
        for r in db.scalars(select(ImportRun)): r.status='succeeded'
    enqueue(client,'lease-lost-http');task=claim(sessions);replacement=[]
    def transport(url,ip,**kwargs):
        if url.endswith('/robots.txt'): return 200,{},b'User-agent: *\nAllow: /101/\n'
        with sessions.begin() as db: db.get(ImportRun,task[0]).lease_expires_at=now()-timedelta(seconds=1)
        replacement.append(claim(sessions))
        return 200,{'content-type':'application/ld+json'},BODY
    def factory(source,before):
        return SafeFetcher(source,before,resolver=lambda *a,**k:['8.8.8.8'],transport=transport)
    process(sessions,task,fetcher_factory=factory)
    with sessions() as db:
        run=db.get(ImportRun,task[0])
        assert run.status=='running' and run.lease_token==replacement[0][1] and run.lease_token!=task[1]
        assert run.records_seen==0 and db.query(EventCandidate).count()==3


def test_shutdown_during_http_starts_no_next_request(complete_api):
    import threading
    from app.imports.fetcher import SafeFetcher
    client,sessions,_=complete_api
    with sessions.begin() as db:
        for r in db.scalars(select(ImportRun)): r.status='succeeded'
    enqueue(client,'shutdown-http');task=claim(sessions);stop=threading.Event();calls=[]
    def transport(url,ip,**kwargs):
        calls.append(url);stop.set()
        return 200,{},b'User-agent: *\nAllow: /101/\n'
    def factory(source,before):
        return SafeFetcher(source,before,resolver=lambda *a,**k:['8.8.8.8'],transport=transport)
    process(sessions,task,stop=stop,fetcher_factory=factory)
    assert len(calls)==1 and calls[0].endswith('/robots.txt')
    with sessions() as db:
        run=db.get(ImportRun,task[0])
        assert run.status=='interrupted' and run.lease_token is None
        assert run.records_seen==0 and db.query(EventCandidate).count()==3
