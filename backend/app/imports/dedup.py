"""Deterministic, bounded suggestions. Never merge or mutate an Event."""
from datetime import timedelta
from difflib import SequenceMatcher

from sqlalchemy import or_, select

from ..models.event import Event
from ..models.imports import CandidateMatch, EventCandidate
from .policy import digest, safe_url, ImportFailure


def event_fingerprint(event):
    return digest({f:getattr(event,f) for f in ('title','datetime','location','organizer_id','event_url','source')})


def suggestions(db, candidate):
    def url_prefix(column,value):
        base=value.split('?',1)[0].split('#',1)[0]
        escaped=base.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        return column.like(escaped+'%',escape='\\')
    predicates = [url_prefix(Event.source,candidate.canonical_source_url)]
    if candidate.official_event_url:
        predicates.append(url_prefix(Event.event_url,candidate.official_event_url))
    if candidate.start_at:
        predicates.append(Event.datetime.between(candidate.start_at-timedelta(minutes=30), candidate.start_at+timedelta(minutes=30)))
    events = list(db.scalars(select(Event).where(or_(*predicates)).order_by(Event.id).limit(201)))
    result = []
    for event in events[:200]:
        reasons = []
        for value, target, reason in [(event.source,candidate.canonical_source_url,'same_source_url'),
                                      (event.event_url,candidate.official_event_url,'same_event_url')]:
            try:
                if value and target and safe_url(value) == safe_url(target):
                    reasons.append(reason)
            except ImportFailure:
                pass
        if candidate.start_at and abs((event.datetime-candidate.start_at).total_seconds()) <= 1800:
            title_score = SequenceMatcher(None,(event.title or '').casefold(),candidate.normalized_title or '').ratio()
            if title_score >= 0.7:
                reasons.extend(['near_time','similar_title'])
                if event.organizer_id and event.organizer_id == candidate.proposed_organizer_id:
                    reasons.append('same_organizer')
                # Event has no city: don't claim a city match from free-text location.
                reasons.append('event_city_unconfirmed')
        if reasons:
            result.append((event,reasons,1 if any(r.startswith('same_') and r.endswith('_url') for r in reasons) else .75))
    if len(events)>200:
        candidate.warnings = list(set(candidate.warnings + ['match_limit_requires_review']))
    return result


def refresh_matches(db,candidate):
    existing = {m.event_id:m for m in db.scalars(select(CandidateMatch).where(CandidateMatch.candidate_id==candidate.id))}
    found = suggestions(db,candidate)
    for event,reasons,score in found:
        match = existing.pop(event.id,None)
        if match is None:
            match=CandidateMatch(candidate_id=candidate.id,event_id=event.id,historical_event_id=event.id)
            db.add(match)
        match.reason_codes=reasons
        match.score=score
        match.compared_event_fingerprint=event_fingerprint(event)
        match.candidate_revision=candidate.revision
        match.decision='suggested'
        match.decided_by=match.decided_at=None
    for match in existing.values():
        db.delete(match)
    db.flush()
    return found


def store_record(db,run,record,source_url):
    candidate=db.scalar(select(EventCandidate).where(EventCandidate.source_id==run.source_id,
        EventCandidate.canonical_source_url==source_url,EventCandidate.source_item_key==record['source_item_key'])
        .with_for_update().execution_options(populate_existing=True))
    created=candidate is None
    from datetime import datetime, timezone
    now=datetime.now(timezone.utc)
    if created:
        candidate=EventCandidate(source_id=run.source_id,first_run_id=run.id,last_run_id=run.id,
            source_url=source_url,canonical_source_url=source_url,source_item_key=record['source_item_key'],
            content_fingerprint=record['fingerprint'],revision=1)
        db.add(candidate)
    elif candidate.content_fingerprint==record['fingerprint']:
        candidate.last_run_id=run.id
        candidate.last_seen_at=now
        return 'unchanged'
    else:
        candidate.revision+=1
        # Keep the prior reviewed snapshot for audit; approval is no longer current.
        if candidate.review_status not in {'converted','linked','rejected'}:
            candidate.review_status='needs_review'
    candidate.last_run_id=run.id
    candidate.last_seen_at=now
    candidate.content_fingerprint=record['fingerprint']
    # Normalized observations, no source HTML/descriptions. JSON serializable only.
    import json
    candidate.observed_payload=json.loads(json.dumps(record['facts'],default=str))
    if candidate.review_status in {'converted','linked'}:
        candidate.warnings=list(set(candidate.warnings+['source_changed_after_link']))
    else:
        for name,value in record['facts'].items():
            setattr(candidate,name,value)
        if candidate.review_status != 'rejected':
            candidate.review_status='needs_review' if (candidate.warnings or not created) else 'pending'
        db.flush()
        refresh_matches(db,candidate)
    db.flush()
    return 'created' if created else 'updated'
