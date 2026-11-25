from datetime import datetime, timezone

from sqlalchemy import Column, Enum, Index, Integer, String, Text

from ..database import Base
from ..utils.event_time import UTCDateTime
from .event_status import PublicationStatus


def utc_now():
    return datetime.now(timezone.utc)


class Article(Base):
    """Blog article. A future city link can be added as a nullable column."""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(120), nullable=False, unique=True)
    excerpt = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    category = Column(String(64), nullable=True)
    seo_title = Column(String(70), nullable=True)
    seo_description = Column(String(200), nullable=True)
    author_name = Column(String(120), nullable=True)
    publication_status = Column(
        Enum(PublicationStatus, values_callable=lambda cls: [item.value for item in cls],
             native_enum=False, create_constraint=True, validate_strings=True,
             name="ck_articles_publication_status"),
        nullable=False, default=PublicationStatus.DRAFT, server_default="draft",
    )
    published_at = Column(UTCDateTime(), nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)
    updated_at = Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_articles_catalog", "publication_status", "published_at"),
        Index("ix_articles_category", "category"),
    )
