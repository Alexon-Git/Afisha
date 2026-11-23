from datetime import datetime
from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from .event import SafeHttpUrl
from .import_review import ReviewInput
from ..utils.event_time import EventInstant


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_id: int = Field(ge=1, le=2147483647, strict=True)
    url: Annotated[SafeHttpUrl, Field(max_length=2048)]


class LinkInput(ReviewInput):
    event_id: int = Field(ge=1, le=2147483647, strict=True)


class CandidateEdit(ReviewInput):
    title: str | None = Field(default=None,min_length=1,max_length=512)
    start_at: EventInstant | None = None
    city: str | None = Field(default=None,max_length=255)
    venue_name: str | None = Field(default=None,max_length=512)
    address: str | None = Field(default=None,max_length=1024)
    official_event_url: Annotated[SafeHttpUrl, Field(max_length=2048)] | None = None
    proposed_organizer_id: int | None = Field(default=None,ge=1,le=2147483647)


class SourceView(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    name:str
    base_url:str
    state:str
    access_method:str
    permission_basis:str|None
    permission_reference:str|None
    terms_url:str|None
    terms_checked_at:datetime|None
    review_due_at:datetime|None
    robots_state:str
    policy_version:int


class RunView(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:UUID
    source_id:int
    requested_url:str
    status:str
    created_at:datetime
    finished_at:datetime|None
    attempt_count:int
    request_count:int
    bytes_received:int
    records_seen:int
    candidates_created:int
    candidates_unchanged:int
    records_rejected:int
    error_code:str|None
    error_summary:str|None
    record_errors:list
