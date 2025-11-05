"""Dependency providers for FastAPI routers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from .database import get_db
from .services.event_service import EventService
from .services.user_service import UserService


def get_event_service(db: Session = Depends(get_db)) -> EventService:
    return EventService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)
