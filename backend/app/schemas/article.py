import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.event_status import PublicationStatus
from ..utils.event_time import EventInstant

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CATEGORY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COVER_RE = re.compile(r"^(/static/uploads/[0-9a-f]{32}\.(?:jpg|png|webp)|https://[^\s<>\"']+)$")


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class ArticleFields(BaseModel):
    """Client-editable fields only; status and timestamps are server controlled."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=120)
    excerpt: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = Field(default=None, max_length=100_000)
    cover_image_url: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=64)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=200)
    author_name: Optional[str] = Field(default=None, max_length=120)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("slug", "excerpt", "content", "cover_image_url", "category",
                     "seo_title", "seo_description", "author_name", mode="before")
    @classmethod
    def blank(cls, value):
        return _blank_to_none(value)

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, value):
        if value is not None and not SLUG_RE.fullmatch(value):
            raise ValueError("Slug: только строчные латинские буквы, цифры и дефисы")
        return value

    @field_validator("category")
    @classmethod
    def valid_category(cls, value):
        if value is not None and not CATEGORY_RE.fullmatch(value):
            raise ValueError("Категория: только строчные латинские буквы, цифры и дефисы")
        return value

    @field_validator("cover_image_url")
    @classmethod
    def valid_cover(cls, value):
        if value is not None and not COVER_RE.fullmatch(value):
            raise ValueError("Обложка: загруженный файл или https-ссылка")
        return value


class ArticleCreate(ArticleFields):
    pass


class ArticleUpdate(ArticleFields):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)


class ArticleOut(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    cover_image_url: Optional[str] = None
    category: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    author_name: Optional[str] = None
    publication_status: PublicationStatus
    published_at: Optional[EventInstant] = None
    created_at: EventInstant
    updated_at: EventInstant

    model_config = ConfigDict(from_attributes=True)


class PublicArticle(BaseModel):
    slug: str
    title: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    cover_image_url: Optional[str] = None
    category: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    author_name: Optional[str] = None
    published_at: EventInstant
    updated_at: EventInstant

    model_config = ConfigDict(from_attributes=True)


class PaginatedArticles(BaseModel):
    items: List[PublicArticle]
    page: int
    limit: int
    total_items: int
    total_pages: int


class AdminPaginatedArticles(BaseModel):
    items: List[ArticleOut]
    page: int
    limit: int
    total_items: int
    total_pages: int
