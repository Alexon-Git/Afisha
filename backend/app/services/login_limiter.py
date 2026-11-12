"""Atomic login reservations shared by all workers using the same database."""

from dataclasses import dataclass
import hashlib
import hmac
from ipaddress import ip_address
import time
from typing import Callable

from sqlalchemy import case, delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..models.login_attempt import LoginAttempt


class LoginLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)


class LoginLimiterUnavailable(Exception):
    """Authentication must fail closed when shared accounting is unavailable."""


@dataclass(frozen=True)
class LoginReservation:
    # Expiry identifies the generation: a late success cannot refund a new window.
    budgets: tuple[tuple[str, int], ...]


class LoginLimiter:
    def __init__(
        self, engine: Engine, *, secret: str, account_limit: int = 5,
        source_limit: int = 30, window_seconds: int = 900,
        clock: Callable[[], float] = time.time,
    ):
        self.engine = engine
        self.secret = secret.encode("utf-8")
        self.account_limit = account_limit
        self.source_limit = source_limit
        self.window_seconds = window_seconds
        self.clock = clock

    def _key(self, kind: str, value: str) -> str:
        digest = hmac.new(self.secret, (kind + "\0" + value).encode("utf-8"), hashlib.sha256)
        return kind + ":" + digest.hexdigest()

    def reserve(self, username: str, source: str) -> LoginReservation:
        """Reserve both budgets atomically BEFORE password hashing (no race gap).

        A failed/interrupted attempt keeps its reservation. Successful requests
        refund only their own slots; previous failures remain until expiry.
        Denied requests roll back both budgets and never extend the window.
        """
        try:
            address = ip_address(source)
            source = str(getattr(address, "ipv4_mapped", None) or address)
        except ValueError:
            pass  # Missing/non-IP ASGI peers share their literal source bucket.
        now = int(self.clock())
        table = LoginAttempt.__table__
        insert = {"sqlite": sqlite_insert, "postgresql": pg_insert}.get(self.engine.dialect.name)
        if insert is None:
            raise LoginLimiterUnavailable()
        budgets = []
        try:
            # Cleanup commits before reserving budgets: do not mix its row-lock
            # order with source/account locking in other workers' transactions.
            with self.engine.begin() as conn:
                expired_keys = select(table.c.key).where(
                    table.c.expires_at <= now,
                ).order_by(table.c.key).limit(100)
                if self.engine.dialect.name == "postgresql":
                    expired_keys = expired_keys.with_for_update(skip_locked=True)
                conn.execute(delete(table).where(table.c.key.in_(expired_keys)))
            with self.engine.begin() as conn:
                # All workers lock source first, then account, in the same order.
                for kind, value, limit in (
                    ("source", source, self.source_limit),
                    ("account", username, self.account_limit),
                ):
                    key = self._key(kind, value)
                    expired = table.c.expires_at <= now
                    statement = insert(table).values(
                        key=key, attempts=1, expires_at=now + self.window_seconds,
                    ).on_conflict_do_update(
                        index_elements=[table.c.key],
                        set_={
                            "attempts": case((expired, 1), else_=table.c.attempts + 1),
                            "expires_at": case((expired, now + self.window_seconds), else_=table.c.expires_at),
                        },
                        where=or_(expired, table.c.attempts < limit),
                    ).returning(table.c.expires_at)
                    expires_at = conn.scalar(statement)
                    if expires_at is None:
                        expires_at = conn.scalar(select(table.c.expires_at).where(table.c.key == key))
                        raise LoginLimitExceeded(expires_at - int(self.clock()))
                    budgets.append((key, expires_at))
        except SQLAlchemyError as exc:
            raise LoginLimiterUnavailable() from exc
        return LoginReservation(tuple(budgets))

    def refund(self, reservation: LoginReservation) -> None:
        table = LoginAttempt.__table__
        try:
            with self.engine.begin() as conn:
                for key, expires_at in reservation.budgets:
                    conn.execute(update(table).where(
                        table.c.key == key, table.c.expires_at == expires_at,
                        table.c.attempts > 0,
                    ).values(attempts=table.c.attempts - 1))
        except SQLAlchemyError as exc:
            raise LoginLimiterUnavailable() from exc
