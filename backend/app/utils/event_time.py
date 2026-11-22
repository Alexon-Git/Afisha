"""Absolute event instants; SQLite encodes UTC, PostgreSQL uses timestamptz."""
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BeforeValidator
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def iso_datetime(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Use ISO 8601 datetime with an explicit UTC offset") from exc
    if not isinstance(value, datetime):
        raise ValueError("Use ISO 8601 datetime with an explicit UTC offset")
    return value


def as_utc(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Event datetime requires an explicit UTC offset")
    try:
        return value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Event instant is outside the supported UTC range") from exc


EventInstant = Annotated[AwareDatetime, BeforeValidator(iso_datetime), AfterValidator(as_utc)]


class UTCDateTime(TypeDecorator):
    """Reject naive writes, preserve instants regardless of process/session TZ."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = as_utc(value)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            value = value.replace(tzinfo=timezone.utc)
        return as_utc(value)
