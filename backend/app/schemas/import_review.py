"""Admin-only import review contract. No Event writes or client-owned audit fields."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReviewStatus = Literal['pending', 'needs_review', 'approved', 'rejected', 'converted', 'linked']


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=1, le=2147483647, strict=True)
    review_note: str | None = Field(default=None, max_length=2048)


class MatchAcknowledgement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    match_id: int = Field(ge=1, le=2147483647, strict=True)
    # Review acknowledgements only; linking/dismissing actual matches is PR-14A.2b.
    decision: Literal['defer', 'not_a_duplicate']


class ApproveCandidate(ReviewInput):
    time_decision: Literal['accept']
    organizer_decision: Literal['accept_proposed', 'unresolved']
    match_decisions: list[MatchAcknowledgement] = Field(max_length=100)

    @model_validator(mode='after')
    def unique_matches(self):
        ids = [item.match_id for item in self.match_decisions]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate match decisions')
        return self


class RejectCandidate(ReviewInput):
    review_note: str = Field(min_length=1, max_length=2048)

    @model_validator(mode='after')
    def reason_required(self):
        if not self.review_note.strip():
            raise ValueError('Rejection reason is required')
        return self


class CandidateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: int
    first_run_id: UUID
    last_run_id: UUID
    title: str | None
    start_at: datetime | None
    normalized_city: str | None
    review_status: ReviewStatus
    revision: int
    discovered_at: datetime
    last_seen_at: datetime
    reviewed_by: int | None
    reviewed_at: datetime | None
    reviewed_revision: int | None
    review_note: str | None
    linked_event_id: int | None
    lost_event_link: bool


class MatchDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    candidate_id: int
    event_id: int | None
    historical_event_id: int
    reason_codes: list
    score: Decimal
    compared_event_fingerprint: str
    created_at: datetime
    candidate_revision: int
    decision: Literal['suggested', 'confirmed', 'dismissed']
    decided_by: int | None
    decided_at: datetime | None


class CandidateDetail(CandidateSummary):
    source_url: str
    canonical_source_url: str
    source_item_key: str
    content_fingerprint: str
    normalized_title: str | None
    neutral_description: str | None
    official_event_url: str | None
    end_at: datetime | None
    original_start: str | None
    time_zone: str | None
    time_resolution: str
    time_evidence: dict
    city: str | None
    venue_name: str | None
    address: str | None
    attendance_mode: str | None
    organizer_name: str | None
    organizer_url: str | None
    proposed_organizer_id: int | None
    price_kind: str
    price_amount: Decimal | None
    price_max: Decimal | None
    currency: str | None
    proposed_event_status: str | None
    warnings: list
    field_provenance: dict
    link_kind: str | None
    linked_at: datetime | None
    reviewed_payload: dict
    observed_payload: dict
    matches: list[MatchDetail] = Field(default_factory=list)


class CandidatePage(BaseModel):
    items: list[CandidateSummary]
    page: int
    limit: int
    total_items: int
    total_pages: int
