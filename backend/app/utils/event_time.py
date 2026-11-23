"""Absolute event instants; SQLite encodes UTC, PostgreSQL uses timestamptz."""
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BeforeValidator
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


EVENT_INSTANT_MIN = datetime(1900, 1, 1, tzinfo=timezone.utc)
EVENT_INSTANT_MAX = datetime(2100, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)


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
        value = value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Event instant is outside the supported UTC range") from exc
    # Leave ample room for driver conversion to a PostgreSQL session timezone.
    # Validate the instant, not its incoming wall-clock year or offset.
    if not EVENT_INSTANT_MIN <= value <= EVENT_INSTANT_MAX:
        raise ValueError("Event instant must be between 1900-01-01T00:00:00Z and 2100-12-31T23:59:59.999999Z")
    return value


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
