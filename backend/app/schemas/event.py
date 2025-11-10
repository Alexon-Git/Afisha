from datetime import datetime as dt_datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from .category import Category


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    datetime: dt_datetime
    location: str
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[int] = None
    rating: Optional[float] = None
    discount: Optional[int] = None
    payment_url: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    datetime: Optional[dt_datetime] = None
    location: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[int] = None
    rating: Optional[float] = None
    discount: Optional[int] = None
    payment_url: Optional[str] = None


class Event(EventBase):
    id: int
    creator_id: Optional[int] = None
    category: Optional[Category] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedEvents(BaseModel):
    items: List[Event]
    page: int
    limit: int
    total_items: int
    total_pages: int
