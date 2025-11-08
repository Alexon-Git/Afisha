from __future__ import annotations

import re
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..models.category import Category
from ..models.event import Event
from ..schemas.category import CategoryCreate, CategoryUpdate
from .exceptions import CategoryAlreadyExistsError, CategoryNotFoundError


class CategoryService:
    """Сервисный слой для управления категориями мероприятий."""

    _SLUG_PATTERN = re.compile(r"[^a-z0-9-_]+")

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_categories(self, *, include_inactive: bool = False) -> List[Category]:
        stmt = select(Category).order_by(Category.name.asc())
        if not include_inactive:
            stmt = stmt.where(Category.is_active.is_(True))
        return list(self._session.scalars(stmt))

    def create_category(self, category_in: CategoryCreate) -> Category:
        name = category_in.name.strip()
        slug = self._normalize_slug(category_in.slug or category_in.name)
        self._ensure_unique_name(name)
        self._ensure_unique_slug(slug)

        category = Category(name=name, slug=slug, is_active=category_in.is_active)
        self._session.add(category)
        self._session.commit()
        self._session.refresh(category)
        return category

    def update_category(self, category_id: int, category_update: CategoryUpdate) -> Category:
        category = self._session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category with id={category_id} does not exist")

        if category_update.name is not None:
            new_name = category_update.name.strip()
            if new_name != category.name:
                self._ensure_unique_name(new_name, exclude_id=category_id)
                category.name = new_name

        if category_update.slug is not None:
            new_slug = self._normalize_slug(category_update.slug)
            if new_slug != category.slug:
                self._ensure_unique_slug(new_slug, exclude_id=category_id)
                category.slug = new_slug

        if category_update.is_active is not None:
            category.is_active = category_update.is_active

        self._session.commit()
        self._session.refresh(category)
        return category

    def delete_category(self, category_id: int) -> None:
        category = self._session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category with id={category_id} does not exist")

        self._session.execute(
            update(Event).where(Event.category_id == category_id).values(category_id=None)
        )
        self._session.delete(category)
        self._session.commit()

    def _ensure_unique_slug(self, slug: str, *, exclude_id: Optional[int] = None) -> None:
        stmt = select(func.count()).select_from(Category).where(func.lower(Category.slug) == slug.lower())
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        exists = self._session.scalar(stmt) or 0
        if exists:
            raise CategoryAlreadyExistsError(f"Category slug '{slug}' already exists")

    def _ensure_unique_name(self, name: str, *, exclude_id: Optional[int] = None) -> None:
        stmt = select(func.count()).select_from(Category).where(func.lower(Category.name) == name.lower())
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        exists = self._session.scalar(stmt) or 0
        if exists:
            raise CategoryAlreadyExistsError(f"Category '{name}' already exists")

    def _normalize_slug(self, slug: str) -> str:
        normalized = slug.strip().lower()
        normalized = normalized.replace(" ", "-")
        normalized = self._SLUG_PATTERN.sub("", normalized)
        return normalized or "category"
