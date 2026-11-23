"""One transaction per editorial action, including Event creation and link."""
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from ..models import Event, EventCandidate, ImportRun, ImportSource, CandidateMatch
from ..models.organizer import Organizer
from ..schemas.event import EventCreate
from ..services.import_review_service import candidate_detail
from .dedup import refresh_matches
from .policy import digest, safe_url, ImportFailure


def locked_candidate(db, cid, revision):
    if db.bind.dialect.name == 'sqlite':
        # End auth's read transaction before acquiring SQLite's write lock.
        db.rollback()
        db.execute(text('BEGIN IMMEDIATE'))
    else:
        # Serializes import conversions, including different candidates.
        db.execute(text('SELECT pg_advisory_xact_lock(14414002)'))
    c=db.scalar(select(EventCandidate).where(EventCandidate.id==cid).with_for_update()
                .execution_options(populate_existing=True))
    if c is None:
        raise HTTPException(404,'Candidate not found')
    if c.revision != revision:
        raise HTTPException(409,'Candidate revision has changed')
    runs=list(db.scalars(select(ImportRun).where(ImportRun.id.in_({c.first_run_id,c.last_run_id})).with_for_update()))
    if len(runs)!=len({c.first_run_id,c.last_run_id}) or any(r.source_id!=c.source_id for r in runs):
        raise HTTPException(409,'Candidate source and runs are inconsistent')
    return c


def approved(c):
    snapshot=c.reviewed_payload
    if (c.review_status!='approved' or c.reviewed_revision!=c.revision
        or snapshot.get('revision')!=c.revision or snapshot.get('content_fingerprint')!=c.content_fingerprint):
        raise HTTPException(409,'Current candidate approval required')
    if c.link_kind or c.linked_event_id or c.lost_event_link:
        raise HTTPException(409,'Candidate already has an Event link')


def transfer(db,cid,change,actor_id,kind):
    try:
        c=locked_candidate(db,cid,change.expected_revision)
        expected_status='converted' if kind=='created' else 'linked'
        # Idempotent exact repeat, including original revision and target.
        if c.review_status==expected_status and c.link_kind==kind and c.linked_event_id is not None:
            if (c.reviewed_revision==c.revision and c.reviewed_payload.get('content_fingerprint')==c.content_fingerprint
                and (kind=='created' or c.linked_event_id==change.event_id)):
                response=candidate_detail(db,c)
                db.commit()
                return response
            raise HTTPException(409,'Different candidate link')
        approved(c)
        if kind=='existing':
            target=db.scalar(select(Event).where(Event.id==change.event_id).with_for_update())
            if target is None:
                raise HTTPException(404,'Event not found')
        else:
            # Recompute matches under the import advisory lock. Newly appeared or
            # changed Events must be explicitly reviewed, never silently dismissed.
            old={m.event_id:(m.id,m.compared_event_fingerprint,m.candidate_revision) for m in db.scalars(
                select(CandidateMatch).where(CandidateMatch.candidate_id==c.id))}
            refresh_matches(db,c)
            current=list(db.scalars(select(CandidateMatch).where(CandidateMatch.candidate_id==c.id)))
            decisions={m['match_id']:m['decision'] for m in c.reviewed_payload.get('match_decisions',[])}
            stale=(set(old)!=set(m.event_id for m in current) or any(
                old.get(m.event_id)!=(m.id,m.compared_event_fingerprint,c.revision) for m in current))
            if stale:
                # Persist only review invalidation; no Event exists yet.
                c.review_status='needs_review'
                db.commit()
                raise HTTPException(409,'Matches changed; review candidate again')
            if any(decisions.get(m.id)!='not_a_duplicate' for m in current) or 'match_limit_requires_review' in c.warnings:
                raise HTTPException(409,'Resolve all potential duplicates before creating a draft')
            if c.start_at is None or c.time_resolution=='ambiguous' or c.normalized_city!='новосибирск':
                raise HTTPException(422,'Resolve time and Novosibirsk location')
            organizer=c.proposed_organizer_id if c.reviewed_payload.get('organizer_decision')=='accept_proposed' else None
            if organizer and db.get(Organizer,organizer) is None:
                raise HTTPException(422,'Organizer not found')
            location=', '.join(filter(None,[c.venue_name,c.address]))
            if not c.title or not c.title.strip() or not location:
                raise HTTPException(422,'Title and location are required')
            price=None
            if c.price_kind=='free':
                price=0
            elif c.price_kind=='fixed' and c.currency=='RUB' and c.price_amount is not None and c.price_amount==int(c.price_amount) and c.price_amount<=2147483647:
                price=int(c.price_amount)
            payload=EventCreate(title=c.title,description=c.neutral_description,datetime=c.start_at,
                location=location,organizer_id=organizer,event_url=c.official_event_url,
                source=safe_url(c.source_url),price=price)
            target=Event(**payload.model_dump(),creator_id=actor_id,publication_status='draft',
                         event_status='scheduled',verified_at=None)
            db.add(target)
            db.flush()
        c.linked_event_id=target.id
        c.link_kind=kind
        c.linked_at=datetime.now(timezone.utc)
        c.review_status=expected_status
        db.flush()
        response=candidate_detail(db,c)
        db.commit()
        return response
    except (ValidationError,ImportFailure,ValueError) as exc:
        db.rollback()
        raise HTTPException(422,'Candidate facts are invalid') from exc
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503,'Import storage unavailable; retry safely') from exc


def edit_candidate(db,cid,change,actor_id):
    try:
        c=locked_candidate(db,cid,change.expected_revision)
        if c.link_kind or c.review_status in {'converted','linked'}:
            raise HTTPException(409,'Linked observations cannot be edited')
        values=change.model_dump(exclude_unset=True,exclude={'expected_revision','review_note'})
        if not values:
            raise HTTPException(422,'No facts to change')
        if values.get('proposed_organizer_id') is not None and db.get(Organizer,values['proposed_organizer_id']) is None:
            raise HTTPException(422,'Organizer not found')
        for name,value in values.items():
            setattr(c,name,value)
        if 'start_at' in values:
            if c.start_at is None:
                c.time_resolution='ambiguous'
            else:
                c.time_resolution='manual_confirmed'
                c.time_evidence={'actor_id':actor_id,'note':change.review_note or 'Explicit editor instant'}
        if 'city' in values:
            c.normalized_city='новосибирск' if (c.city or '').casefold() in {'новосибирск','novosibirsk'} else None
        if 'title' in values:
            c.normalized_title=(c.title or '').casefold().replace('ё','е')
        c.revision+=1
        c.content_fingerprint=digest({name:getattr(c,name) for name in (
            'title','start_at','city','venue_name','address','official_event_url','proposed_organizer_id')})
        c.review_status='needs_review'
        refresh_matches(db,c)
        db.flush()
        response=candidate_detail(db,c)
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503,'Import storage unavailable') from exc
