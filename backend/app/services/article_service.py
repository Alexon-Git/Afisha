"""Blog article storage and editorial workflow."""
import math
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, asc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.article import Article
from ..models.event_status import PublicationStatus
from ..schemas.article import ArticleCreate, ArticleUpdate
from .exceptions import ArticleConflictError, ArticleNotFoundError, ArticleValidationError

_TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                     ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p", "r", "s", "t",
                      "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))
MIN_CONTENT = 200


def slugify(text: str, limit: int = 120) -> str:
    value = "".join(_TRANSLIT.get(ch, ch) for ch in text.lower())
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:limit].strip("-")


class ArticleService:
    def __init__(self, session: Session) -> None:
        self._s = session

    # ---- public ----
    def list_public(self, *, page=1, limit=12, category: Optional[str] = None, sort="desc"):
        return self._page(page, limit, category, sort, public=True)

    def get_public(self, slug: str) -> Article:
        item = self._s.scalar(select(Article).where(
            Article.slug == slug, Article.publication_status == PublicationStatus.PUBLISHED))
        if item is None:
            raise ArticleNotFoundError()
        return item

    # ---- admin ----
    def list_admin(self, *, page=1, limit=20, status: Optional[str] = None):
        return self._page(page, limit, None, "desc", public=False, status=status)

    def get(self, article_id: int) -> Article:
        item = self._s.get(Article, article_id)
        if item is None:
            raise ArticleNotFoundError()
        return item

    def create(self, data: ArticleCreate) -> Article:
        values = data.model_dump()
        values["slug"] = values["slug"] or slugify(values["title"])
        if not values["slug"]:
            raise ArticleValidationError({"slug": "Не удалось построить slug, укажите его вручную"})
        item = Article(**values, publication_status=PublicationStatus.DRAFT)
        self._s.add(item)
        self._commit()
        return item

    def update(self, article_id: int, data: ArticleUpdate) -> Article:
        item = self.get(article_id)
        patch = data.model_dump(exclude_unset=True)
        if patch.get("title", "x") is None:
            raise ArticleValidationError({"title": "Заголовок обязателен"})
        if patch.get("slug") is None and "slug" in patch:
            patch.pop("slug")
        if "slug" in patch and patch["slug"] != item.slug and item.published_at is not None:
            raise ArticleConflictError("Slug статьи, которая уже публиковалась, изменить нельзя")
        for key, value in patch.items():
            setattr(item, key, value)
        if item.publication_status == PublicationStatus.PUBLISHED:
            self._validate_publishable(item)
        self._commit()
        return item

    def publish(self, article_id: int) -> Article:
        item = self.get(article_id)
        self._validate_publishable(item)
        if item.publication_status != PublicationStatus.PUBLISHED:
            item.publication_status = PublicationStatus.PUBLISHED
            if item.published_at is None:
                item.published_at = datetime.now(timezone.utc)
        self._commit()
        return item

    def unpublish(self, article_id: int) -> Article:
        item = self.get(article_id)
        item.publication_status = PublicationStatus.DRAFT
        self._commit()
        return item

    def archive(self, article_id: int) -> Article:
        item = self.get(article_id)
        item.publication_status = PublicationStatus.ARCHIVED
        self._commit()
        return item

    def published_slugs(self):
        return self._s.execute(select(Article.slug, Article.updated_at).where(
            Article.publication_status == PublicationStatus.PUBLISHED).order_by(Article.slug)).all()

    # ---- internals ----
    @staticmethod
    def _validate_publishable(item: Article) -> None:
        errors = {}
        if not (item.title or "").strip():
            errors["title"] = "Заголовок обязателен"
        if not item.slug:
            errors["slug"] = "Slug обязателен"
        if len((item.content or "").strip()) < MIN_CONTENT:
            errors["content"] = f"Нужен текст не короче {MIN_CONTENT} символов"
        if not item.excerpt:
            errors["excerpt"] = "Нужно краткое описание"
        if not item.seo_description:
            errors["seo_description"] = "Нужно SEO-описание"
        if errors:
            raise ArticleValidationError(errors)

    def _commit(self) -> None:
        try:
            self._s.commit()
        except IntegrityError as exc:
            self._s.rollback()
            raise ArticleConflictError("Статья с таким slug уже существует") from exc

    def _page(self, page, limit, category, sort, *, public, status=None):
        page = max(1, page)
        limit = min(max(1, limit), 50)
        query = select(Article)
        if public:
            query = query.where(Article.publication_status == PublicationStatus.PUBLISHED)
            if category:
                query = query.where(Article.category == category)
            order = Article.published_at
        else:
            if status in {s.value for s in PublicationStatus}:
                query = query.where(Article.publication_status == PublicationStatus(status))
            order = Article.updated_at
        total = self._s.scalar(select(func.count()).select_from(query.subquery())) or 0
        direction = asc if sort == "asc" else desc
        rows = self._s.scalars(query.order_by(direction(order), direction(Article.id))
                               .offset((page - 1) * limit).limit(limit)).all()
        return {"items": rows, "page": page, "limit": limit, "total_items": total,
                "total_pages": math.ceil(total / limit)}
