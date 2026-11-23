"""Read and review import candidates. No fetch, link, promote, or publication."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..auth.auth import get_current_admin_user
from ..database import get_db
from ..models.imports import EventCandidate
from ..models.user import User
from ..schemas.import_review import ApproveCandidate, CandidateDetail, CandidatePage, RejectCandidate, ReviewStatus
from ..services.import_review_service import candidate_detail, moderate_candidate

router = APIRouter(prefix='/admin/import/candidates', tags=['admin-import-candidates'],
                   dependencies=[Depends(get_current_admin_user)])
PositiveId = Annotated[int, Query(ge=1, le=2147483647)]


@router.get('', response_model=CandidatePage)
def list_candidates(page: Annotated[int, Query(ge=1, le=2147483647)] = 1,
                    limit: Annotated[int, Query(ge=1, le=100)] = 20,
                    source_id: PositiveId | None = None,
                    run_id: UUID | None = None,
                    review_status: ReviewStatus | None = None,
                    normalized_city: Annotated[str | None, Query(max_length=255)] = None,
                    db: Session = Depends(get_db)):
    query = select(EventCandidate)
    if source_id is not None:
        query = query.where(EventCandidate.source_id == source_id)
    if run_id is not None:
        query = query.where((EventCandidate.first_run_id == run_id) | (EventCandidate.last_run_id == run_id))
    if review_status is not None:
        query = query.where(EventCandidate.review_status == review_status)
    if normalized_city is not None:
        query = query.where(EventCandidate.normalized_city == normalized_city)
    try:
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        items = db.scalars(query.order_by(EventCandidate.discovered_at.desc(), EventCandidate.id.desc())
                           .offset((page - 1) * limit).limit(limit)).all()
        return dict(items=items, page=page, limit=limit, total_items=total,
                    total_pages=(total + limit - 1) // limit)
    except SQLAlchemyError as exc:
        raise HTTPException(503, 'Import review storage unavailable') from exc


@router.get('/{candidate_id}', response_model=CandidateDetail)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    try:
        candidate = db.get(EventCandidate, candidate_id)
        if candidate is None:
            raise HTTPException(404, 'Candidate not found')
        return candidate_detail(db, candidate)
    except SQLAlchemyError as exc:
        raise HTTPException(503, 'Import review storage unavailable') from exc


@router.post('/{candidate_id}/approve', response_model=CandidateDetail)
def approve(candidate_id: int, change: ApproveCandidate, db: Session = Depends(get_db),
            actor: User = Depends(get_current_admin_user)):
    return moderate_candidate(db, candidate_id, change, actor.id, 'approved')


@router.post('/{candidate_id}/reject', response_model=CandidateDetail)
def reject(candidate_id: int, change: RejectCandidate, db: Session = Depends(get_db),
           actor: User = Depends(get_current_admin_user)):
    return moderate_candidate(db, candidate_id, change, actor.id, 'rejected')
