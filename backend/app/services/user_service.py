"""Service responsible for user related operations."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..models.user import User
from ..schemas.user import UserCreate
from .exceptions import UserAlreadyExistsError

logger = logging.getLogger(__name__)

PasswordHasher = Callable[[str], str]


class UserService:
    """High level API for working with users."""

    def __init__(self, session: Session, *, password_hasher: Optional[PasswordHasher] = None) -> None:
        self._session = session
        self._password_hasher = password_hasher

    def get_by_username(self, username: str) -> Optional[User]:
        return self._session.query(User).filter(User.username == username).first()

    def register_user(self, user_in: UserCreate) -> User:
        existing = self.get_by_username(user_in.username)
        if existing:
            raise UserAlreadyExistsError(f"User '{user_in.username}' already exists")

        hashed_password = self._get_password_hasher()(user_in.password)
        db_user = User(
            username=user_in.username,
            password_hash=hashed_password,
            email=user_in.email,
            is_admin=False,
        )
        self._session.add(db_user)
        self._session.commit()
        self._session.refresh(db_user)
        logger.info("Registered new user '%s'", db_user.username)
        return db_user

    def _get_password_hasher(self) -> PasswordHasher:
        if self._password_hasher is not None:
            return self._password_hasher
        from ..auth.auth import get_password_hash  # Local import to avoid circular dependency

        return get_password_hash
