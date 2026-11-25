"""Authenticated editorial API for blog articles."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from ..auth.auth import get_current_admin_user
from ..dependencies import get_article_service, get_event_service
from ..schemas.article import AdminPaginatedArticles, ArticleCreate, ArticleOut, ArticleUpdate
from ..services.article_service import ArticleService
from ..services.event_service import EventService
from ..services.exceptions import (ArticleConflictError, ArticleNotFoundError, ArticleValidationError,
                                   InvalidImageError)

router = APIRouter(prefix="/admin/articles", tags=["admin-articles"],
                   dependencies=[Depends(get_current_admin_user)])


def run(action):
    try:
        return action()
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Article not found") from exc
    except ArticleConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ArticleValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "fields": exc.fields}) from exc


@router.get("/", response_model=AdminPaginatedArticles)
def list_articles(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50),
                  status: Optional[str] = None, service: ArticleService = Depends(get_article_service)):
    return service.list_admin(page=page, limit=limit, status=status)


@router.post("/upload-cover")
def upload_cover(file: UploadFile, events: EventService = Depends(get_event_service)):
    # Reuses the existing validated, re-encoding image pipeline.
    try:
        return {"image_url": events.save_image(file)}
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, service: ArticleService = Depends(get_article_service)):
    return run(lambda: service.get(article_id))


@router.post("/", response_model=ArticleOut, status_code=201)
def create_article(data: ArticleCreate, service: ArticleService = Depends(get_article_service)):
    return run(lambda: service.create(data))


@router.put("/{article_id}", response_model=ArticleOut)
def update_article(article_id: int, data: ArticleUpdate, service: ArticleService = Depends(get_article_service)):
    return run(lambda: service.update(article_id, data))


@router.post("/{article_id}/publish", response_model=ArticleOut)
def publish(article_id: int, service: ArticleService = Depends(get_article_service)):
    return run(lambda: service.publish(article_id))


@router.post("/{article_id}/unpublish", response_model=ArticleOut)
def unpublish(article_id: int, service: ArticleService = Depends(get_article_service)):
    return run(lambda: service.unpublish(article_id))


@router.post("/{article_id}/archive", response_model=ArticleOut)
def archive(article_id: int, service: ArticleService = Depends(get_article_service)):
    return run(lambda: service.archive(article_id))
