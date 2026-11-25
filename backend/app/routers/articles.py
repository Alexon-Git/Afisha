"""Public blog API: only published articles are ever returned."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func

from ..database import get_db
from ..dependencies import get_article_service
from ..models.article import Article
from ..models.event_status import PublicationStatus
from ..schemas.article import PaginatedArticles, PublicArticle
from ..services.article_service import ArticleService
from ..services.exceptions import ArticleNotFoundError

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/", response_model=PaginatedArticles)
def list_articles(page: int = Query(1, ge=1), limit: int = Query(12, ge=1, le=50),
                  category: Optional[str] = Query(None, max_length=64),
                  sort: str = Query("desc", pattern="^(asc|desc)$"),
                  service: ArticleService = Depends(get_article_service)):
    return service.list_public(page=page, limit=limit, category=category, sort=sort)


@router.get("/categories", response_model=list[str])
def list_categories(db=Depends(get_db)):
    rows = db.scalars(select(Article.category).where(
        Article.publication_status == PublicationStatus.PUBLISHED, Article.category.is_not(None))
        .group_by(Article.category).order_by(Article.category)).all()
    return list(rows)


@router.get("/{slug}", response_model=PublicArticle)
def get_article(slug: str, service: ArticleService = Depends(get_article_service)):
    try:
        return service.get_public(slug)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Article not found") from exc
