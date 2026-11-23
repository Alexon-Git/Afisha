"""Add import storage, preserving existing application tables and data.

Revision ID: 0005_import_schema
Revises: 0004_event_datetime_utc
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005_import_schema'
down_revision = '0004_event_datetime_utc'
branch_labels = None
depends_on = None

def upgrade():

    op.create_table('import_sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('base_url', sa.String(length=2048), nullable=False),
    sa.Column('base_origin', sa.String(length=255), nullable=False),
    sa.Column('base_path', sa.String(length=1024), nullable=False),
    sa.Column('source_type', sa.String(length=32), nullable=False),
    sa.Column('adapter_key', sa.String(length=64), nullable=False),
    sa.Column('access_method', sa.String(length=32), server_default='manual_only', nullable=False),
    sa.Column('allowed_origins', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='[]', nullable=False),
    sa.Column('allowed_path_prefixes', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='[]', nullable=False),
    sa.Column('state', sa.String(length=32), server_default='pending_review', nullable=False),
    sa.Column('terms_url', sa.String(length=2048), nullable=True),
    sa.Column('permission_basis', sa.String(length=32), nullable=True),
    sa.Column('permission_reference', sa.String(length=1024), nullable=True),
    sa.Column('terms_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('terms_checked_by', sa.Integer(), nullable=True),
    sa.Column('review_due_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('robots_state', sa.String(length=32), server_default='unknown', nullable=False),
    sa.Column('robots_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('robots_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('robots_hash', sa.String(length=64), nullable=True),
    sa.Column('robots_rules', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='{}', nullable=False),
    sa.Column('policy_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('request_interval_seconds', sa.Integer(), server_default='60', nullable=False),
    sa.Column('next_request_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('blocked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("access_method IN ('manual_only', 'jsonld_html', 'partner_api')", name='ck_import_access_method'),
    sa.CheckConstraint("permission_basis IN ('published_terms', 'written_permission', 'api_agreement')", name='ck_import_permission_basis'),
    sa.CheckConstraint("robots_state IN ('unknown', 'allowed', 'denied', 'approved_absent', 'not_applicable_api')", name='ck_import_robots_state'),
    sa.CheckConstraint("source_type IN ('official_site', 'approved_aggregator', 'partner_api')", name='ck_import_source_type'),
    sa.CheckConstraint("state IN ('pending_review', 'enabled', 'paused', 'prohibited')", name='ck_import_state'),
    sa.CheckConstraint('length(CAST(allowed_origins AS TEXT)) <= 16384', name='ck_import_allowed_origins_size'),
    sa.CheckConstraint('length(CAST(allowed_path_prefixes AS TEXT)) <= 16384', name='ck_import_allowed_path_prefixes_size'),
    sa.CheckConstraint('length(CAST(robots_rules AS TEXT)) <= 16384', name='ck_import_robots_rules_size'),
    sa.CheckConstraint('policy_version >= 1 AND request_interval_seconds >= 1', name='ck_import_source_policy'),
    sa.ForeignKeyConstraint(['terms_checked_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('base_origin', 'base_path', 'access_method', name='uq_import_source_identity')
    )
    op.create_table('import_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('requested_by', sa.Integer(), nullable=False),
    sa.Column('requested_url', sa.String(length=2048), nullable=False),
    sa.Column('canonical_url', sa.String(length=2048), nullable=True),
    sa.Column('final_url', sa.String(length=2048), nullable=True),
    sa.Column('status', sa.String(length=32), server_default='queued', nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('lease_token', sa.Uuid(), nullable=True),
    sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('policy_version', sa.Integer(), nullable=False),
    sa.Column('adapter_version', sa.String(length=64), nullable=False),
    sa.Column('request_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('bytes_received', sa.Integer(), server_default='0', nullable=False),
    sa.Column('records_seen', sa.Integer(), server_default='0', nullable=False),
    sa.Column('candidates_created', sa.Integer(), server_default='0', nullable=False),
    sa.Column('candidates_unchanged', sa.Integer(), server_default='0', nullable=False),
    sa.Column('records_rejected', sa.Integer(), server_default='0', nullable=False),
    sa.Column('error_code', sa.String(length=64), nullable=True),
    sa.Column('error_summary', sa.String(length=1024), nullable=True),
    sa.Column('record_errors', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='[]', nullable=False),
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('request_fingerprint', sa.String(length=64), nullable=False),
    sa.Column('recheck_candidate_id', sa.Integer(), nullable=True),
    sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'partial', 'blocked', 'failed', 'interrupted')", name='ck_import_status'),
    sa.CheckConstraint('bytes_received >= 0', name='ck_import_run_bytes_received'),
    sa.CheckConstraint('candidates_created >= 0', name='ck_import_run_candidates_created'),
    sa.CheckConstraint('candidates_unchanged >= 0', name='ck_import_run_candidates_unchanged'),
    sa.CheckConstraint('length(CAST(record_errors AS TEXT)) <= 16384', name='ck_import_record_errors_size'),
    sa.CheckConstraint('policy_version >= 1', name='ck_import_run_policy_version'),
    sa.CheckConstraint('records_rejected >= 0', name='ck_import_run_records_rejected'),
    sa.CheckConstraint('records_seen >= 0', name='ck_import_run_records_seen'),
    sa.CheckConstraint('request_count >= 0', name='ck_import_run_request_count'),
    sa.ForeignKeyConstraint(['recheck_candidate_id'], ['event_candidates.id'], name='fk_import_run_recheck_candidate', ondelete='SET NULL', use_alter=True),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_id'], ['import_sources.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('requested_by', 'idempotency_key', name='uq_import_run_idempotency')
    )
    op.create_index(op.f('ix_import_runs_source_id'), 'import_runs', ['source_id'], unique=False)
    op.create_index('ix_import_runs_status_created_at', 'import_runs', ['status', 'created_at'], unique=False)
    op.create_index('uq_import_runs_running_source', 'import_runs', ['source_id'], unique=True, postgresql_where=sa.text("status = 'running'"), sqlite_where=sa.text("status = 'running'"))
    op.create_table('event_candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('first_run_id', sa.Uuid(), nullable=False),
    sa.Column('last_run_id', sa.Uuid(), nullable=False),
    sa.Column('source_url', sa.String(length=2048), nullable=False),
    sa.Column('canonical_source_url', sa.String(length=2048), nullable=False),
    sa.Column('source_item_key', sa.String(length=512), nullable=False),
    sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('content_fingerprint', sa.String(length=64), nullable=False),
    sa.Column('revision', sa.Integer(), server_default='1', nullable=False),
    sa.Column('title', sa.String(length=512), nullable=True),
    sa.Column('normalized_title', sa.String(length=512), nullable=True),
    sa.Column('neutral_description', sa.String(length=2048), nullable=True),
    sa.Column('official_event_url', sa.String(length=2048), nullable=True),
    sa.Column('start_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('original_start', sa.String(length=255), nullable=True),
    sa.Column('time_zone', sa.String(length=64), nullable=True),
    sa.Column('time_resolution', sa.String(length=32), server_default='ambiguous', nullable=False),
    sa.Column('time_evidence', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='{}', nullable=False),
    sa.Column('city', sa.String(length=255), nullable=True),
    sa.Column('normalized_city', sa.String(length=255), nullable=True),
    sa.Column('venue_name', sa.String(length=512), nullable=True),
    sa.Column('address', sa.String(length=1024), nullable=True),
    sa.Column('attendance_mode', sa.String(length=32), nullable=True),
    sa.Column('organizer_name', sa.String(length=255), nullable=True),
    sa.Column('organizer_url', sa.String(length=2048), nullable=True),
    sa.Column('proposed_organizer_id', sa.Integer(), nullable=True),
    sa.Column('price_kind', sa.String(length=16), server_default='unknown', nullable=False),
    sa.Column('price_amount', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('price_max', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('proposed_event_status', sa.String(length=16), nullable=True),
    sa.Column('review_status', sa.String(length=32), server_default='pending', nullable=False),
    sa.Column('warnings', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='[]', nullable=False),
    sa.Column('field_provenance', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='{}', nullable=False),
    sa.Column('reviewed_by', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_revision', sa.Integer(), nullable=True),
    sa.Column('review_note', sa.String(length=2048), nullable=True),
    sa.Column('linked_event_id', sa.Integer(), nullable=True),
    sa.Column('link_kind', sa.String(length=16), nullable=True),
    sa.Column('linked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lost_event_link', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('reviewed_payload', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='{}', nullable=False),
    sa.Column('observed_payload', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='{}', nullable=False),
    sa.CheckConstraint("link_kind IN ('created', 'existing')", name='ck_import_link_kind'),
    sa.CheckConstraint("price_kind IN ('unknown', 'free', 'fixed', 'from', 'range')", name='ck_import_price_kind'),
    sa.CheckConstraint("proposed_event_status IN ('scheduled', 'cancelled', 'postponed')", name='ck_import_proposed_event_status'),
    sa.CheckConstraint("review_status IN ('pending', 'needs_review', 'approved', 'rejected', 'converted', 'linked')", name='ck_import_review_status'),
    sa.CheckConstraint("time_resolution IN ('explicit_offset', 'manual_confirmed', 'ambiguous')", name='ck_import_time_resolution'),
    sa.CheckConstraint('(price_amount IS NULL OR price_amount >= 0) AND (price_max IS NULL OR price_max >= 0) AND (price_amount IS NULL OR price_max IS NULL OR price_max >= price_amount)', name='ck_import_candidate_price'),
    sa.CheckConstraint('end_at IS NULL OR start_at IS NULL OR end_at >= start_at', name='ck_import_candidate_time_order'),
    sa.CheckConstraint('length(CAST(field_provenance AS TEXT)) <= 16384', name='ck_import_field_provenance_size'),
    sa.CheckConstraint('length(CAST(observed_payload AS TEXT)) <= 16384', name='ck_import_observed_payload_size'),
    sa.CheckConstraint('length(CAST(reviewed_payload AS TEXT)) <= 16384', name='ck_import_reviewed_payload_size'),
    sa.CheckConstraint('length(CAST(time_evidence AS TEXT)) <= 16384', name='ck_import_time_evidence_size'),
    sa.CheckConstraint('length(CAST(warnings AS TEXT)) <= 16384', name='ck_import_warnings_size'),
    sa.CheckConstraint('revision >= 1 AND (reviewed_revision IS NULL OR (reviewed_revision >= 1 AND reviewed_revision <= revision))', name='ck_import_candidate_revision'),
    sa.ForeignKeyConstraint(['first_run_id'], ['import_runs.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['last_run_id'], ['import_runs.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['linked_event_id'], ['events.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['proposed_organizer_id'], ['organizers.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_id'], ['import_sources.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_id', 'canonical_source_url', 'source_item_key', name='uq_import_candidate_identity')
    )
    op.create_index(op.f('ix_event_candidates_linked_event_id'), 'event_candidates', ['linked_event_id'], unique=False)
    op.create_index(op.f('ix_event_candidates_normalized_city'), 'event_candidates', ['normalized_city'], unique=False)
    op.create_index('ix_event_candidates_review_discovered', 'event_candidates', ['review_status', 'discovered_at'], unique=False)
    op.create_index(op.f('ix_event_candidates_start_at'), 'event_candidates', ['start_at'], unique=False)
    op.create_table('import_candidate_matches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=True),
    sa.Column('historical_event_id', sa.Integer(), nullable=False),
    sa.Column('reason_codes', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='[]', nullable=False),
    sa.Column('score', sa.Numeric(precision=10, scale=6), nullable=False),
    sa.Column('compared_event_fingerprint', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('candidate_revision', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=16), server_default='suggested', nullable=False),
    sa.Column('decided_by', sa.Integer(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("decision IN ('suggested', 'confirmed', 'dismissed')", name='ck_import_decision'),
    sa.CheckConstraint('candidate_revision >= 1', name='ck_import_match_revision'),
    sa.CheckConstraint('event_id IS NULL OR historical_event_id = event_id', name='ck_import_match_history'),
    sa.CheckConstraint('length(CAST(reason_codes AS TEXT)) <= 16384', name='ck_import_reason_codes_size'),
    sa.CheckConstraint('score >= 0', name='ck_import_match_score'),
    sa.ForeignKeyConstraint(['candidate_id'], ['event_candidates.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('candidate_id', 'event_id', name='uq_import_candidate_match')
    )
    op.create_index(op.f('ix_import_candidate_matches_event_id'), 'import_candidate_matches', ['event_id'], unique=False)


    if op.get_bind().dialect.name == 'postgresql':
        # The run/candidate recheck cycle is added after both new tables exist.
        op.create_foreign_key('fk_import_run_recheck_candidate', 'import_runs',
                              'event_candidates', ['recheck_candidate_id'], ['id'], ondelete='SET NULL')
    _create_link_warning_triggers()


def _create_link_warning_triggers():
    # Triggers live only on new import tables. Existing Event DELETE remains valid.
    if op.get_bind().dialect.name == 'postgresql':
        op.execute("""
            CREATE FUNCTION import_lost_event_link() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_TABLE_NAME = 'event_candidates' THEN
                    NEW.lost_event_link := true;
                ELSE
                    EXECUTE format('UPDATE %I.event_candidates SET lost_event_link = true WHERE id = $1', TG_TABLE_SCHEMA)
                    USING NEW.candidate_id;
                END IF;
                RETURN NEW;
            END;
            $$
        """)
        for table, field in [('event_candidates', 'linked_event_id'), ('import_candidate_matches', 'event_id')]:
            op.execute(f"""CREATE TRIGGER import_lost_event_link BEFORE UPDATE OF {field} ON {table}
                FOR EACH ROW WHEN (OLD.{field} IS NOT NULL AND NEW.{field} IS NULL)
                EXECUTE FUNCTION import_lost_event_link()""")
    elif op.get_bind().dialect.name == 'sqlite':
        for table, field, candidate in [('event_candidates', 'linked_event_id', 'NEW.id'),
                                         ('import_candidate_matches', 'event_id', 'NEW.candidate_id')]:
            op.execute(f"""CREATE TRIGGER {table}_lost_event_link AFTER UPDATE OF {field} ON {table}
                WHEN OLD.{field} IS NOT NULL AND NEW.{field} IS NULL
                BEGIN
                    UPDATE event_candidates SET lost_event_link = true WHERE id = {candidate};
                END""")


def downgrade():
    # Destructive: import history is removed; production rollback needs a separate plan.
    if op.get_bind().dialect.name == 'postgresql':
        op.drop_constraint('fk_import_run_recheck_candidate', 'import_runs', type_='foreignkey')
        op.execute('DROP TRIGGER import_lost_event_link ON event_candidates')
        op.execute('DROP TRIGGER import_lost_event_link ON import_candidate_matches')
        op.execute('DROP FUNCTION import_lost_event_link()')
    elif op.get_bind().dialect.name == 'sqlite':
        op.execute('DROP TRIGGER event_candidates_lost_event_link')
        op.execute('DROP TRIGGER import_candidate_matches_lost_event_link')


    op.drop_index(op.f('ix_import_candidate_matches_event_id'), table_name='import_candidate_matches')
    op.drop_table('import_candidate_matches')
    op.drop_index(op.f('ix_event_candidates_start_at'), table_name='event_candidates')
    op.drop_index('ix_event_candidates_review_discovered', table_name='event_candidates')
    op.drop_index(op.f('ix_event_candidates_normalized_city'), table_name='event_candidates')
    op.drop_index(op.f('ix_event_candidates_linked_event_id'), table_name='event_candidates')
    op.drop_table('event_candidates')
    op.drop_index('uq_import_runs_running_source', table_name='import_runs', postgresql_where=sa.text("status = 'running'"), sqlite_where=sa.text("status = 'running'"))
    op.drop_index('ix_import_runs_status_created_at', table_name='import_runs')
    op.drop_index(op.f('ix_import_runs_source_id'), table_name='import_runs')
    op.drop_table('import_runs')
    op.drop_table('import_sources')
