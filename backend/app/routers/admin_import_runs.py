"""Read policy, enqueue, inspect; permissions/leases are never client-owned."""
from functools import wraps
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..auth.auth import get_current_admin_user
from ..database import get_db
from ..models import ImportRun, ImportSource, EventCandidate
from ..models.user import User
from ..schemas.import_actions import RunInput, RunView, SourceView
from ..imports.policy import ImportFailure, check_policy, check_url, digest
from ..imports.jsonld import VERSION

router=APIRouter(prefix='/admin/import',tags=['admin-import-runs'],dependencies=[Depends(get_current_admin_user)])
Page=Annotated[int,Query(ge=1,le=2147483647)]
Limit=Annotated[int,Query(ge=1,le=100)]


def queue(db,data,actor_id,key,recheck_id=None):
    try:
        source=db.scalar(select(ImportSource).where(ImportSource.id==data.source_id).with_for_update())
        if source is None:
            raise HTTPException(404,'Source not found')
        check_policy(source)
        url=check_url(source,data.url)
        fingerprint=digest({'source':source.id,'url':url,'candidate':recheck_id})
        previous=db.scalar(select(ImportRun).where(ImportRun.requested_by==actor_id,ImportRun.idempotency_key==key))
        if previous:
            if previous.request_fingerprint!=fingerprint:
                raise HTTPException(409,'Idempotency key belongs to a different request')
            response=RunView.model_validate(previous)
            db.commit()
            return response
        # Bounded queue per source; source row lock makes the quota multi-process.
        count=db.scalar(select(func.count()).select_from(ImportRun).where(ImportRun.source_id==source.id,ImportRun.status.in_(['queued','running'])))
        if count>=10:
            raise HTTPException(429,'Source queue is full',headers={'Retry-After':'60'})
        run=ImportRun(source_id=source.id,requested_by=actor_id,requested_url=url,canonical_url=url,
            policy_version=source.policy_version,adapter_version=VERSION,idempotency_key=key,
            request_fingerprint=fingerprint,recheck_candidate_id=recheck_id)
        db.add(run)
        db.flush()
        response=RunView.model_validate(run)
        db.commit()
        return response
    except ImportFailure as exc:
        db.rollback()
        raise HTTPException(422,exc.code) from exc
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503,'Import storage unavailable; retry with the same key') from exc


def storage_read(action):
    @wraps(action)
    def protected(*args,**kwargs):
        try:
            return action(*args,**kwargs)
        except SQLAlchemyError as exc:
            kwargs['db'].rollback()
            raise HTTPException(503,'Import storage unavailable') from exc
    return protected


@router.get('/sources',response_model=list[SourceView])
@storage_read
def sources(page:Page=1,limit:Limit=20,db:Session=Depends(get_db)):
    return list(db.scalars(select(ImportSource).order_by(ImportSource.id).offset((page-1)*limit).limit(limit)))


@router.post('/runs',response_model=RunView,status_code=202)
def start(data:RunInput,idempotency_key:Annotated[str,Header(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9_-]+$')],
          db:Session=Depends(get_db),actor:User=Depends(get_current_admin_user)):
    return queue(db,data,actor.id,idempotency_key)


@router.get('/runs',response_model=list[RunView])
@storage_read
def runs(page:Page=1,limit:Limit=20,db:Session=Depends(get_db)):
    return list(db.scalars(select(ImportRun).order_by(ImportRun.created_at.desc(),ImportRun.id).offset((page-1)*limit).limit(limit)))


@router.get('/runs/{run_id}',response_model=RunView)
@storage_read
def run_detail(run_id:UUID,db:Session=Depends(get_db)):
    run=db.get(ImportRun,run_id)
    if run is None:
        raise HTTPException(404,'Run not found')
    return run


@router.post('/candidates/{candidate_id}/recheck',response_model=RunView,status_code=202)
@storage_read
def recheck(candidate_id:int,idempotency_key:Annotated[str,Header(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9_-]+$')],
            db:Session=Depends(get_db),actor:User=Depends(get_current_admin_user)):
    candidate=db.get(EventCandidate,candidate_id)
    if candidate is None:
        raise HTTPException(404,'Candidate not found')
    return queue(db,RunInput(source_id=candidate.source_id,url=candidate.canonical_source_url),actor.id,idempotency_key,candidate.id)
