"""Service responsible for working with events."""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, joinedload

from ..models.category import Category
from ..models.event import Event
from ..schemas.event import EventCreate, EventUpdate
from .exceptions import CategoryNotFoundError, EventNotFoundError, InvalidDateFilterError, InvalidImageError

logger = logging.getLogger(__name__)


class EventService:
    """High level API for querying and mutating events."""

    _MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
    _MAX_IMAGE_PIXELS = 20_000_000
    _IMAGE_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    _BASE_DIR = Path(__file__).resolve().parents[1]
    _UPLOAD_DIR = _BASE_DIR / "static" / "uploads"

    def __init__(self, session: Session) -> None:
        self._session = session
        self._UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def list_events(
        self,
        *,
        page: int = 1,
        limit: int = 10,
        date: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        category: Optional[str] = None,
        sort: Optional[str] = "asc",
    ) -> Dict[str, object]:
        """Return paginated events according to provided filters."""

        page = max(page, 1)
        limit = max(1, min(limit, 100))

        # Validate before category lookup: an unknown category must not hide bad dates.
        start, end = self._resolve_date_filters(date=date, date_from=date_from, date_to=date_to)
        filters = []
        if category:
            category_obj = self._session.scalar(
                select(Category).where(Category.slug == category, Category.is_active.is_(True))
            )
            if not category_obj:
                return {
                    "items": [],
                    "page": page,
                    "limit": limit,
                    "total_items": 0,
                    "total_pages": 0,
                }
            filters.append(Event.category_id == category_obj.id)

        if start:
            filters.append(Event.datetime >= start)
        if end:
            filters.append(Event.datetime < end)

        order_expression = self._get_sorting_expression(sort)

        items_stmt = (
            select(Event)
            .options(joinedload(Event.category))
            .where(*filters)
            .order_by(order_expression)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        items = list(self._session.scalars(items_stmt))

        count_stmt = select(func.count()).select_from(Event)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total_items = self._session.scalar(count_stmt) or 0
        total_pages = math.ceil(total_items / limit) if total_items else 0

        return {
            "items": items,
            "page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": total_pages,
        }

    def get_event(self, event_id: int) -> Event:
        stmt = select(Event).options(joinedload(Event.category)).where(Event.id == event_id)
        event = self._session.scalar(stmt)
        if event is None:
            raise EventNotFoundError(f"Event with id={event_id} does not exist")
        return event

    def create_event(self, event_in: EventCreate, *, creator_id: Optional[int]) -> Event:
        self._validate_category(event_in.category_id)
        db_event = Event(**event_in.model_dump(), creator_id=creator_id)
        self._session.add(db_event)
        self._session.commit()
        self._session.refresh(db_event)
        if db_event.category_id:
            _ = db_event.category
        return db_event

    def update_event(self, event_id: int, event_update: EventUpdate) -> Event:
        db_event = self._session.get(Event, event_id)
        if db_event is None:
            raise EventNotFoundError(f"Event with id={event_id} does not exist")

        update_data = event_update.model_dump(exclude_unset=True)
        if "category_id" in update_data:
            self._validate_category(update_data["category_id"])
        for field, value in update_data.items():
            setattr(db_event, field, value)

        self._session.commit()
        self._session.refresh(db_event)
        if db_event.category_id:
            _ = db_event.category
        return db_event

    def _validate_category(self, category_id: Optional[int]) -> None:
        if category_id is not None and self._session.get(Category, category_id) is None:
            raise CategoryNotFoundError("Category not found")

    def delete_event(self, event_id: int) -> None:
        db_event = self._session.get(Event, event_id)
        if db_event is None:
            raise EventNotFoundError(f"Event with id={event_id} does not exist")

        if db_event.image_url:
            self._remove_image(db_event.image_url)

        self._session.delete(db_event)
        self._session.commit()

    def save_image(self, file: UploadFile) -> str:
        if not file.filename:
            raise InvalidImageError("File must have a name")
        file.file.seek(0)
        content = file.file.read(self._MAX_UPLOAD_SIZE + 1)
        if len(content) > self._MAX_UPLOAD_SIZE:
            raise InvalidImageError("File size must be less than 5MB")

        try:
            with Image.open(BytesIO(content), formats=list(self._IMAGE_EXTENSIONS)) as image:
                image_format = image.format
                if image.width * image.height > self._MAX_IMAGE_PIXELS:
                    raise InvalidImageError("Image must not exceed 20 million pixels")
                if getattr(image, "n_frames", 1) != 1:
                    raise InvalidImageError("Animated images are not supported")
                image.verify()

            # verify() checks structure; load() also checks the compressed pixels.
            # Re-encode instead of publishing the untrusted original bytes.
            with Image.open(BytesIO(content), formats=list(self._IMAGE_EXTENSIONS)) as image:
                image.load()
                ImageOps.exif_transpose(image, in_place=True)
                with image.convert("RGB" if image_format == "JPEG" else "RGBA") as clean_image:
                    clean_image.info.clear()
                    output = BytesIO()
                    clean_image.save(output, format=image_format)
                    content = output.getvalue()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
            raise InvalidImageError("File must be a valid JPG, PNG or WebP image") from exc

        if len(content) > self._MAX_UPLOAD_SIZE:
            raise InvalidImageError("Encoded image must be less than 5MB")

        filename = f"{uuid4().hex}{self._IMAGE_EXTENSIONS[image_format]}"
        file_path = self._UPLOAD_DIR / filename

        with file_path.open("xb") as buffer:
            try:
                buffer.write(content)
            except OSError:
                file_path.unlink(missing_ok=True)
                raise

        return f"/static/uploads/{filename}"

    def _resolve_date_filters(
        self,
        *,
        date: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        if date_from is not None or date_to is not None:
            start = self._parse_iso_date(date_from) if date_from is not None else None
            last = self._parse_iso_date(date_to) if date_to is not None else None
            # A single supplied boundary still selects one calendar day.
            start = start if start is not None else last
            last = last if last is not None else start
            if start > last:
                raise InvalidDateFilterError("date_from must be before date_to")
        elif date is None:
            return None, None
        else:
            if date in ("today", "tomorrow", "weekend"):
                # Only the calendar day uses a zone; SQL boundaries stay naive
                # until the separate historical-data/timestamptz migration.
                today = datetime.now(ZoneInfo("Asia/Novosibirsk")).date()
                start = datetime(today.year, today.month, today.day)
                if date == "tomorrow":
                    start += timedelta(days=1)
                elif date == "weekend":
                    # Sunday belongs to the current weekend, not the next one.
                    days_until_sat = -1 if today.weekday() == 6 else (5 - today.weekday()) % 7
                    start += timedelta(days=days_until_sat)
                last = start + timedelta(days=1) if date == "weekend" else start
            else:
                start = last = self._parse_iso_date(date)
        try:
            return start, last + timedelta(days=1)
        except OverflowError as exc:
            raise InvalidDateFilterError("Last calendar day must be before 9999-12-31") from exc

    def _parse_iso_date(self, value: Optional[str]) -> datetime:
        if not value or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise InvalidDateFilterError("Date must use YYYY-MM-DD format")
        try:
            y, m, d = map(int, value.split("-"))
            return datetime(y, m, d, 0, 0, 0)
        except (TypeError, ValueError) as exc:
            raise InvalidDateFilterError("Invalid calendar date") from exc

    def _get_sorting_expression(self, sort: Optional[str]):
        if sort == "desc":
            return desc(Event.datetime)
        return asc(Event.datetime)

    def _remove_image(self, image_url: str) -> None:
        image_path = self._UPLOAD_DIR / Path(image_url).name
        if image_path.exists():
            try:
                image_path.unlink()
            except OSError as exc:
                logger.warning("Failed to delete image '%s': %s", image_path, exc)
