from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    datetime: datetime
    location: str
    image_url: Optional[str] = None
    category: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    datetime: Optional[datetime] = None
    location: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None


class Event(EventBase):
    id: int
    creator_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedEvents(BaseModel):
    items: List[Event]
    page: int
    limit: int
    total_items: int
    total_pages: int
