from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from typing import List


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    datetime: datetime
    location: str
    image_url: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    datetime: Optional[datetime] = None
    location: Optional[str] = None
    image_url: Optional[str] = None


class Event(EventBase):
    id: int
    creator_id: Optional[int] = None

    class Config:
        from_attributes = True


class PaginatedEvents(BaseModel):
    items: List[Event]
    page: int
    limit: int
    total_items: int
    total_pages: int
