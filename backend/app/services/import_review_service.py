"""Atomic candidate decisions; deliberately has no Event service dependency."""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, update, text
from sqlalchemy.exc import SQLAlchemyError

from ..models.imports import CandidateMatch, EventCandidate, ImportRun, ImportSource
from ..schemas.import_review import CandidateDetail, MatchDetail


def candidate_detail(db, candidate):
    result = CandidateDetail.model_validate(candidate)
    result.matches = [MatchDetail.model_validate(row) for row in db.scalars(
        select(CandidateMatch).where(CandidateMatch.candidate_id == candidate.id)
        .order_by(CandidateMatch.id))]
    return result


def moderate_candidate(db, candidate_id, change, actor_id, decision):
    try:
        if db.bind.dialect.name == 'postgresql':
            db.execute(text('SELECT pg_advisory_xact_lock(14414002)'))
        # Auth has already read through this session. Lock + refresh prevents a
        # cached ORM object from hiding another editor's committed decision.
        candidate = db.scalar(select(EventCandidate).where(EventCandidate.id == candidate_id)
                              .with_for_update().execution_options(populate_existing=True))
        if candidate is None:
            raise HTTPException(404, 'Candidate not found')
        if candidate.revision != change.expected_revision:
            raise HTTPException(409, 'Candidate revision has changed')
        if candidate.review_status not in {'pending', 'needs_review'}:
            raise HTTPException(409, 'Candidate has already been reviewed or linked')
        if candidate.linked_event_id is not None or candidate.link_kind is not None:
            raise HTTPException(409, 'Candidate already has an Event link')
        # Existing independent FKs do not enforce this cross-table invariant.
        # Lock the referenced runs while checking; all moderation fails closed.
        source = db.scalar(select(ImportSource).where(ImportSource.id == candidate.source_id).with_for_update())
        runs = list(db.scalars(select(ImportRun).where(ImportRun.id.in_(
            {candidate.first_run_id, candidate.last_run_id})).order_by(ImportRun.id).with_for_update()))
        if (source is None or len(runs) != len({candidate.first_run_id, candidate.last_run_id})
                or any(run.source_id != candidate.source_id for run in runs)):
            raise HTTPException(409, 'Candidate source and runs are inconsistent')

        values = dict(review_status=decision, reviewed_by=actor_id,
                      reviewed_at=datetime.now(timezone.utc), reviewed_revision=candidate.revision,
                      review_note=change.review_note)
        if decision == 'approved':
            if candidate.start_at is None or candidate.time_resolution == 'ambiguous':
                raise HTTPException(422, 'Time must be resolved before approval')
            if change.organizer_decision == 'accept_proposed' and candidate.proposed_organizer_id is None:
                raise HTTPException(422, 'No proposed organizer to accept')
            matches = list(db.scalars(select(CandidateMatch).where(
                CandidateMatch.candidate_id == candidate.id).order_by(CandidateMatch.id).with_for_update()))
            if {m.id for m in matches} != {m.match_id for m in change.match_decisions}:
                raise HTTPException(409, 'Acknowledge every current match of this candidate')
            if any(m.candidate_revision != candidate.revision for m in matches):
                raise HTTPException(409, 'Candidate matches refer to an outdated revision')
            # Snapshot only bounded stored facts plus bounded explicit decisions.
            # No arbitrary client payload, actor, status, timestamps, or link IDs.
            values['reviewed_payload'] = {
                'revision': candidate.revision,
                'content_fingerprint': candidate.content_fingerprint,
                'time_decision': change.time_decision,
                'organizer_decision': change.organizer_decision,
                'match_decisions': [m.model_dump() for m in change.match_decisions],
            }
        else:
            values['reviewed_payload'] = {}
        # CAS is also required on SQLite, where SELECT FOR UPDATE is ignored.
        result = db.execute(update(EventCandidate).where(
            EventCandidate.id == candidate.id,
            EventCandidate.revision == change.expected_revision,
            EventCandidate.review_status == candidate.review_status,
            EventCandidate.source_id == candidate.source_id,
            EventCandidate.first_run_id == candidate.first_run_id,
            EventCandidate.last_run_id == candidate.last_run_id,
        ).values(**values).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise HTTPException(409, 'Concurrent candidate change')
        db.refresh(candidate)
        response = candidate_detail(db, candidate)
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503, 'Import review storage unavailable') from exc
