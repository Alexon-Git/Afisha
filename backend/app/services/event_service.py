"""Service responsible for working with events."""

from __future__ import annotations

import logging
import math
import shutil
from datetime import datetime, timedelta
from os import SEEK_END, SEEK_SET
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from ..models.event import Event
from ..schemas.event import EventCreate, EventUpdate
from .exceptions import EventNotFoundError, InvalidDateFilterError, InvalidImageError

logger = logging.getLogger(__name__)


class EventService:
    """High level API for querying and mutating events."""

    _MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
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

        filters = []
        if category:
            filters.append(Event.category == category)

        try:
            start, end = self._resolve_date_filters(date=date, date_from=date_from, date_to=date_to)
        except InvalidDateFilterError as exc:
            logger.warning("Unable to apply date filter: %s", exc)
            start = end = None

        if start:
            filters.append(Event.datetime >= start)
        if end:
            filters.append(Event.datetime <= end)

        order_expression = self._get_sorting_expression(sort)

        items_stmt = (
            select(Event)
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
        event = self._session.get(Event, event_id)
        if event is None:
            raise EventNotFoundError(f"Event with id={event_id} does not exist")
        return event

    def create_event(self, event_in: EventCreate, *, creator_id: Optional[int]) -> Event:
        db_event = Event(**event_in.model_dump(), creator_id=creator_id)
        self._session.add(db_event)
        self._session.commit()
        self._session.refresh(db_event)
        return db_event

    def update_event(self, event_id: int, event_update: EventUpdate) -> Event:
        db_event = self._session.get(Event, event_id)
        if db_event is None:
            raise EventNotFoundError(f"Event with id={event_id} does not exist")

        update_data = event_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_event, field, value)

        self._session.commit()
        self._session.refresh(db_event)
        return db_event

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
        if not file.content_type or not file.content_type.startswith("image/"):
            raise InvalidImageError("File must be an image")

        file.file.seek(0, SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0, SEEK_SET)
        if file_size > self._MAX_UPLOAD_SIZE:
            raise InvalidImageError("File size must be less than 5MB")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = Path(file.filename).name.replace(" ", "_")
        filename = f"{timestamp}_{safe_name}"
        file_path = self._UPLOAD_DIR / filename

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return f"/static/uploads/{filename}"

    def _resolve_date_filters(
        self,
        *,
        date: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        if date_from or date_to:
            start = self._parse_iso_date(date_from) if date_from else None
            end = self._parse_iso_date(date_to) if date_to else None
            if start and not end:
                end = start.replace(hour=23, minute=59, second=59)
            elif end and not start:
                start = end.replace(hour=0, minute=0, second=0)
            if start and end and start > end:
                raise InvalidDateFilterError("date_from must be before date_to")
            return start, end
        if not date:
            return None, None

        now = datetime.now()
        start: Optional[datetime] = None
        end: Optional[datetime] = None
        if date == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(hour=23, minute=59, second=59)
        elif date == "tomorrow":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            end = start.replace(hour=23, minute=59, second=59)
        elif date == "weekend":
            weekday = now.weekday()
            days_until_sat = (5 - weekday) % 7
            start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sat)
            end = start + timedelta(days=1, hours=23, minutes=59, seconds=59)
        else:
            start = self._parse_iso_date(date)
            end = start.replace(hour=23, minute=59, second=59)
        return start, end

    def _parse_iso_date(self, value: Optional[str]) -> datetime:
        if not value:
            raise InvalidDateFilterError("Date value is missing")
        try:
            y, m, d = map(int, value.split("-"))
            return datetime(y, m, d, 0, 0, 0)
        except (TypeError, ValueError) as exc:
            raise InvalidDateFilterError(f"Invalid date format: {value}") from exc

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
