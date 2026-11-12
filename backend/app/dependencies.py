"""Dependency providers for FastAPI routers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from .database import engine, get_db
from .config import settings
from .services.login_limiter import LoginLimiter
from .services.category_service import CategoryService
from .services.event_service import EventService
from .services.user_service import UserService


def get_event_service(db: Session = Depends(get_db)) -> EventService:
    return EventService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(db)


def get_login_limiter() -> LoginLimiter:
    return LoginLimiter(
        engine, secret=settings.secret_key,
        account_limit=settings.login_account_limit,
        source_limit=settings.login_source_limit,
        window_seconds=settings.login_window_seconds,
    )
