from datetime import datetime as dt_datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    price: Optional[int] = Field(default=None, ge=0)
    rating: Optional[float] = Field(default=None, ge=0, le=10)
    discount: Optional[int] = Field(default=None, ge=0, le=100)


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    datetime: Optional[dt_datetime] = None
    location: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[int] = Field(default=None, ge=0)
    rating: Optional[float] = Field(default=None, ge=0, le=10)
    discount: Optional[int] = Field(default=None, ge=0, le=100)
    payment_url: Optional[str] = None

    @field_validator("title", "datetime", "location")
    @classmethod
    def required_fields_cannot_be_null(cls, value):
        # Validators run for explicitly supplied fields, not omitted defaults.
        if value is None:
            raise ValueError("Field cannot be null")
        return value


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
