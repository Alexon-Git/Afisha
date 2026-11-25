"""Bounded import facts and audit history; imports never publish Events."""
from uuid import uuid4

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Column, ForeignKey, Index, Integer, Numeric,
    String, UniqueConstraint, Uuid, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB

from ..database import Base
from ..utils.pricing import CandidateMoney
from ..utils.event_time import UTCDateTime


def choice(field, values):
    literals = ', '.join(repr(value) for value in values.split())
    return CheckConstraint(f"{field} IN ({literals})", name=f"ck_import_{field}")


def stamp(**kwargs):
    return Column(UTCDateTime(), **kwargs)


def document(default):
    return Column(JSON().with_variant(JSONB(), 'postgresql'), nullable=False,
                  default=list if default == '[]' else dict, server_default=default)


def bounded_documents(*names):
    return tuple(CheckConstraint(f"length(CAST({name} AS TEXT)) <= 16384",
                                 name=f"ck_import_{name}_size") for name in names)


class ImportSource(Base):
    __tablename__ = 'import_sources'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    base_url = Column(String(2048), nullable=False)
    # Persist normalized components explicitly for source identity.
    base_origin = Column(String(255), nullable=False)
    base_path = Column(String(1024), nullable=False)
    source_type = Column(String(32), nullable=False)
    adapter_key = Column(String(64), nullable=False)
    access_method = Column(String(32), nullable=False, server_default='manual_only')
    allowed_origins = document('[]')
    allowed_path_prefixes = document('[]')
    state = Column(String(32), nullable=False, server_default='pending_review')
    terms_url = Column(String(2048))
    permission_basis = Column(String(32))
    permission_reference = Column(String(1024))
    terms_checked_at = stamp()
    terms_checked_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    review_due_at = stamp()
    robots_state = Column(String(32), nullable=False, server_default='unknown')
    robots_checked_at = stamp()
    robots_expires_at = stamp()
    robots_hash = Column(String(64))
    robots_rules = document('{}')
    policy_version = Column(Integer, nullable=False, server_default='1')
    request_interval_seconds = Column(Integer, nullable=False, server_default='60')
    next_request_at = stamp()
    blocked_until = stamp()
    created_at = stamp(nullable=False, server_default=func.now())
    updated_at = stamp(nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint('base_origin', 'base_path', 'access_method', name='uq_import_source_identity'),
        choice('source_type', 'official_site approved_aggregator partner_api'),
        choice('access_method', 'manual_only jsonld_html partner_api'),
        choice('state', 'pending_review enabled paused prohibited'),
        choice('permission_basis', 'published_terms written_permission api_agreement'),
        choice('robots_state', 'unknown allowed denied approved_absent not_applicable_api'),
        CheckConstraint('policy_version >= 1 AND request_interval_seconds >= 1', name='ck_import_source_policy'),
        *bounded_documents('allowed_origins', 'allowed_path_prefixes', 'robots_rules'),
    )


class ImportRun(Base):
    __tablename__ = 'import_runs'
    id = Column(Uuid, primary_key=True, default=uuid4)
    source_id = Column(Integer, ForeignKey('import_sources.id', ondelete='RESTRICT'), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    requested_url = Column(String(2048), nullable=False)
    canonical_url = Column(String(2048))
    final_url = Column(String(2048))
    status = Column(String(32), nullable=False, server_default='queued')
    started_at = stamp()
    finished_at = stamp()
    created_at = stamp(nullable=False, server_default=func.now())
    lease_token = Column(Uuid)
    lease_expires_at = stamp()
    heartbeat_at = stamp()
    policy_version = Column(Integer, nullable=False)
    adapter_version = Column(String(64), nullable=False)
    attempt_count = Column(Integer, nullable=False, server_default='0')
    request_count = Column(Integer, nullable=False, server_default='0')
    bytes_received = Column(Integer, nullable=False, server_default='0')
    records_seen = Column(Integer, nullable=False, server_default='0')
    candidates_created = Column(Integer, nullable=False, server_default='0')
    candidates_unchanged = Column(Integer, nullable=False, server_default='0')
    records_rejected = Column(Integer, nullable=False, server_default='0')
    error_code = Column(String(64))
    error_summary = Column(String(1024))
    record_errors = document('[]')
    idempotency_key = Column(String(128), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    recheck_candidate_id = Column(Integer, ForeignKey(
        'event_candidates.id', name='fk_import_run_recheck_candidate', ondelete='SET NULL', use_alter=True))
    __table_args__ = (
        choice('status', 'queued running succeeded partial blocked failed interrupted'),
        UniqueConstraint('requested_by', 'idempotency_key', name='uq_import_run_idempotency'),
        CheckConstraint('policy_version >= 1', name='ck_import_run_policy_version'),
        *(CheckConstraint(f'{name} >= 0', name=f'ck_import_run_{name}') for name in (
            'request_count', 'bytes_received', 'records_seen', 'candidates_created',
            'candidates_unchanged', 'records_rejected')),
        Index('ix_import_runs_status_created_at', 'status', 'created_at'),
        Index('uq_import_runs_running_source', 'source_id', unique=True,
              postgresql_where=text("status = 'running'"), sqlite_where=text("status = 'running'")),
        *bounded_documents('record_errors'),
    )


class EventCandidate(Base):
    __tablename__ = 'event_candidates'
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('import_sources.id', ondelete='RESTRICT'), nullable=False)
    first_run_id = Column(Uuid, ForeignKey('import_runs.id', ondelete='RESTRICT'), nullable=False)
    last_run_id = Column(Uuid, ForeignKey('import_runs.id', ondelete='RESTRICT'), nullable=False)
    source_url = Column(String(2048), nullable=False)
    canonical_source_url = Column(String(2048), nullable=False)
    source_item_key = Column(String(512), nullable=False)
    discovered_at = stamp(nullable=False, server_default=func.now())
    last_seen_at = stamp(nullable=False, server_default=func.now())
    content_fingerprint = Column(String(64), nullable=False)
    revision = Column(Integer, nullable=False, server_default='1')
    title = Column(String(512))
    normalized_title = Column(String(512))
    neutral_description = Column(String(2048))
    official_event_url = Column(String(2048))
    start_at = stamp(index=True)
    end_at = stamp()
    original_start = Column(String(255))
    time_zone = Column(String(64))
    time_resolution = Column(String(32), nullable=False, server_default='ambiguous')
    time_evidence = document('{}')
    city = Column(String(255))
    normalized_city = Column(String(255), index=True)
    venue_name = Column(String(512))
    address = Column(String(1024))
    attendance_mode = Column(String(32))
    organizer_name = Column(String(255))
    organizer_url = Column(String(2048))
    proposed_organizer_id = Column(Integer, ForeignKey('organizers.id', ondelete='SET NULL'))
    price_kind = Column(String(16), nullable=False, server_default='unknown')
    price_amount = Column(CandidateMoney())
    price_max = Column(CandidateMoney())
    currency = Column(String(3))
    proposed_event_status = Column(String(16))
    review_status = Column(String(32), nullable=False, server_default='pending')
    warnings = document('[]')
    field_provenance = document('{}')
    reviewed_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    reviewed_at = stamp()
    reviewed_revision = Column(Integer)
    review_note = Column(String(2048))
    linked_event_id = Column(Integer, ForeignKey('events.id', ondelete='SET NULL'), index=True)
    link_kind = Column(String(16))
    linked_at = stamp()
    lost_event_link = Column(Boolean, nullable=False, server_default=text('false'))
    reviewed_payload = document('{}')
    observed_payload = document('{}')
    __table_args__ = (
        UniqueConstraint('source_id', 'canonical_source_url', 'source_item_key', name='uq_import_candidate_identity'),
        choice('time_resolution', 'explicit_offset manual_confirmed ambiguous'),
        choice('price_kind', 'unknown free fixed from range'),
        choice('proposed_event_status', 'scheduled cancelled postponed'),
        choice('review_status', 'pending needs_review approved rejected converted linked'),
        choice('link_kind', 'created existing'),
        CheckConstraint('revision >= 1 AND (reviewed_revision IS NULL OR (reviewed_revision >= 1 AND reviewed_revision <= revision))', name='ck_import_candidate_revision'),
        CheckConstraint('end_at IS NULL OR start_at IS NULL OR end_at >= start_at', name='ck_import_candidate_time_order'),
        CheckConstraint('(price_amount IS NULL OR price_amount >= 0) AND (price_max IS NULL OR price_max >= 0) AND (price_amount IS NULL OR price_max IS NULL OR price_max >= price_amount)', name='ck_import_candidate_price'),
        Index('ix_event_candidates_review_discovered', 'review_status', 'discovered_at'),
        *bounded_documents('time_evidence', 'warnings', 'field_provenance', 'reviewed_payload', 'observed_payload'),
    )


class CandidateMatch(Base):
    __tablename__ = 'import_candidate_matches'
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey('event_candidates.id', ondelete='RESTRICT'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='SET NULL'), index=True)
    historical_event_id = Column(Integer, nullable=False)  # Snapshot, deliberately not a FK.
    reason_codes = document('[]')
    score = Column(Numeric(10, 6), nullable=False)
    compared_event_fingerprint = Column(String(64), nullable=False)
    created_at = stamp(nullable=False, server_default=func.now())
    candidate_revision = Column(Integer, nullable=False)
    decision = Column(String(16), nullable=False, server_default='suggested')
    decided_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    decided_at = stamp()
    __table_args__ = (
        UniqueConstraint('candidate_id', 'event_id', name='uq_import_candidate_match'),
        choice('decision', 'suggested confirmed dismissed'),
        CheckConstraint('candidate_revision >= 1', name='ck_import_match_revision'),
        CheckConstraint('score >= 0', name='ck_import_match_score'),
        CheckConstraint('event_id IS NULL OR historical_event_id = event_id', name='ck_import_match_history'),
        *bounded_documents('reason_codes'),
    )
