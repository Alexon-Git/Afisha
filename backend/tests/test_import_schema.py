"""Import schema: SQLite and opt-in isolated PostgreSQL 17, synthetic facts only."""
from datetime import datetime, timezone
from decimal import Decimal
import os
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models import CandidateMatch, EventCandidate, ImportRun, ImportSource
from test_event_metadata_migration import upgrade

NEW = {'import_sources', 'import_runs', 'event_candidates', 'import_candidate_matches'}


@pytest.fixture(scope='module', params=['sqlite', 'postgresql'])
def import_database(request, tmp_path_factory):
    if request.param == 'postgresql':
        value = os.environ.get('AFISHA_PR14_TEST_DATABASE_URL')
        if not value:
            pytest.skip('Isolated PostgreSQL URL not supplied')
        base = make_url(value)
        if base.host != '127.0.0.1' or (base.database, base.username) not in {('afisha_pr14', 'pr14_test'), ('afisha_pr8', 'pr8_test')}:
            pytest.fail('Only designated isolated local PostgreSQL is allowed')
        admin = create_engine(base)
        schema = 'pr14_' + uuid4().hex
        with admin.begin() as c:
            assert c.execute(text('SHOW server_version_num')).scalar().startswith('17')
            c.execute(text(f'CREATE SCHEMA {schema}'))
        url = base.update_query_dict({'options': f'-csearch_path={schema}'}).render_as_string(hide_password=False)
    else:
        url = f"sqlite:///{tmp_path_factory.mktemp('imports') / 'test.db'}"
    engine = create_engine(url)
    if request.param == 'sqlite':
        @event.listens_for(engine, 'connect')
        def foreign_keys(c, _):
            c.execute('PRAGMA foreign_keys=ON')
    try:
        upgrade(url, '0004_event_datetime_utc')
        with engine.begin() as c:
            for sql in [
                "INSERT INTO users (id,username,password_hash,is_admin) VALUES (1,'synthetic','not-real',true)",
                "INSERT INTO categories (id,name,slug,is_active) VALUES (1,'Synthetic','synthetic',true)",
                "INSERT INTO organizers (id,name) VALUES (1,'Synthetic club')",
                "INSERT INTO events (id,title,datetime,location,organizer_id,creator_id,category_id) VALUES (1,'Existing','2026-11-23 11:00:00+00:00','NSK',1,1,1)",
                "INSERT INTO login_attempts VALUES ('synthetic',2,1800000000)",
            ]:
                c.execute(text(sql))
            tables = set(inspect(c).get_table_names()) - {'alembic_version'}
            before = {t: c.execute(text(f'SELECT * FROM {t}')).mappings().all() for t in tables}
            structure = {t: repr((inspect(c).get_columns(t), inspect(c).get_indexes(t), inspect(c).get_foreign_keys(t))) for t in tables}
        upgrade(url, 'head')
        upgrade(url, 'head')
        with engine.connect() as c:
            assert set(inspect(c).get_table_names()) == tables | NEW | {'alembic_version'}
            assert c.execute(text('SELECT version_num FROM alembic_version')).scalar() == '0005_import_schema'
            for t in tables:
                assert c.execute(text(f'SELECT * FROM {t}')).mappings().all() == before[t]
                assert repr((inspect(c).get_columns(t), inspect(c).get_indexes(t), inspect(c).get_foreign_keys(t))) == structure[t]
            assert compare_metadata(MigrationContext.configure(c, opts={'compare_type': True, 'compare_server_default': True}), Base.metadata) == []
            for t in NEW:
                assert c.execute(text(f'SELECT count(*) FROM {t}')).scalar() == 0
        yield engine
    finally:
        engine.dispose()
        if request.param == 'postgresql':
            with admin.begin() as c:
                c.execute(text(f'DROP SCHEMA {schema} CASCADE'))  # Only this random test schema.
            admin.dispose()


@pytest.fixture
def storage(import_database):
    with import_database.connect() as c:
        outer = c.begin()
        with Session(bind=c, join_transaction_mode='create_savepoint') as db:
            source = ImportSource(id=1, name='Synthetic', base_url='https://example.invalid/events',
                base_origin='https://example.invalid', base_path='/events', source_type='official_site', adapter_key='jsonld_html')
            db.add(source)
            db.flush()
            run = ImportRun(source_id=1, requested_by=1, requested_url=source.base_url, policy_version=1,
                adapter_version='v1', idempotency_key='test', request_fingerprint='a'*64)
            db.add(run)
            db.flush()
            candidate = EventCandidate(id=1, source_id=1, first_run_id=run.id, last_run_id=run.id,
                source_url=source.base_url, canonical_source_url=source.base_url, source_item_key='one', content_fingerprint='b'*64)
            db.add(candidate)
            db.flush()
            yield db, source, run, candidate
        outer.rollback()


def test_defaults_and_no_autopublication(storage):
    db, source, run, candidate = storage
    assert (source.state, source.robots_state, source.access_method) == ('pending_review', 'unknown', 'manual_only')
    assert source.allowed_origins == source.allowed_path_prefixes == []
    assert source.created_at.utcoffset().total_seconds() == 0
    assert run.status == 'queued' and run.request_count == run.bytes_received == 0
    assert candidate.review_status == 'pending' and candidate.time_resolution == 'ambiguous'
    assert candidate.price_kind == 'unknown' and candidate.price_amount is None
    assert candidate.start_at is candidate.linked_event_id is None
    assert candidate.warnings == [] and candidate.observed_payload == {}
    for status in ['needs_review', 'approved', 'rejected', 'converted', 'linked']:
        candidate.review_status = status
        db.flush()
        assert db.execute(text('SELECT count(*) FROM events')).scalar() == 1
        assert db.execute(text('SELECT count(*) FROM organizers')).scalar() == 1
        assert tuple(db.execute(text('SELECT publication_status,verified_at FROM events')).one()) == ('draft', None)


@pytest.mark.parametrize('model,field,value', [
    *[(ImportSource, f, 'invalid') for f in ['state', 'source_type', 'access_method', 'permission_basis', 'robots_state']],
    (ImportSource, 'policy_version', 0), (ImportSource, 'request_interval_seconds', 0),
    (ImportRun, 'status', 'invalid'), (ImportRun, 'policy_version', 0),
    *[(ImportRun, f, -1) for f in ['request_count', 'bytes_received', 'records_seen', 'candidates_created', 'candidates_unchanged', 'records_rejected']],
    *[(EventCandidate, f, 'invalid') for f in ['review_status', 'time_resolution', 'price_kind', 'proposed_event_status', 'link_kind']],
    (EventCandidate, 'revision', 0), (EventCandidate, 'reviewed_revision', 2),
    (EventCandidate, 'price_amount', -1), (EventCandidate, 'price_max', -1),
    (EventCandidate, 'linked_event_id', 99999), (EventCandidate, 'proposed_organizer_id', 99999),
    (ImportRun, 'recheck_candidate_id', 99999), (EventCandidate, 'warnings', ['x'*16385]),
])
def test_constraints(storage, model, field, value):
    db, *_ = storage
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(model.__table__.update().values({field: value}))


def test_unique_and_restrict(storage):
    db, source, run, candidate = storage
    for model, original in [(ImportSource, source), (ImportRun, run), (EventCandidate, candidate)]:
        values = {col.name: getattr(original, col.name) for col in model.__table__.columns if col.name != 'id'}
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(model.__table__.insert().values(**values))
    second = ImportRun(source_id=1, requested_by=1, requested_url=source.base_url, policy_version=1,
        adapter_version='v1', idempotency_key='second', request_fingerprint='c'*64)
    db.add(second)
    db.flush()  # Multiple queued runs allowed.
    run.status = 'running'
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(ImportRun.__table__.update().where(ImportRun.id == second.id).values(status='running'))
    for table in [ImportSource.__table__, ImportRun.__table__]:
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(table.delete())


@pytest.mark.parametrize('linked', [False, True])
def test_event_deletion_preserves_history(storage, linked):
    db, _, run, candidate = storage
    if linked:
        candidate.linked_event_id, candidate.link_kind = 1, 'existing'
    match = CandidateMatch(candidate_id=1, event_id=1, historical_event_id=1, reason_codes=['same_time'],
        score=Decimal('0.750000'), compared_event_fingerprint='c'*64, candidate_revision=1)
    db.add(match)
    run.recheck_candidate_id = 1
    db.flush()
    assert match.decision == 'suggested'
    for values in [dict(decision='invalid'), dict(score=-1), dict(candidate_revision=0), dict(historical_event_id=2)]:
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(CandidateMatch.__table__.update().values(**values))
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(CandidateMatch.__table__.insert().values(candidate_id=1, event_id=1, historical_event_id=1,
            reason_codes=[], score=1, compared_event_fingerprint='d'*64, candidate_revision=1))
    db.execute(text('DELETE FROM events WHERE id=1'))
    db.expire_all()
    assert candidate.linked_event_id is None and candidate.lost_event_link is True
    assert match.event_id is None and match.historical_event_id == 1 and match.reason_codes == ['same_time']
    assert match.score == Decimal('0.750000')
    assert db.query(CandidateMatch).count() == 1


def test_time_and_decimal(storage):
    db, _, _, candidate = storage
    instant = datetime(2026, 11, 23, 11, tzinfo=timezone.utc)
    candidate.start_at = candidate.end_at = instant
    candidate.price_amount, candidate.price_max = Decimal('123.4567'), Decimal('200.0001')
    db.flush()
    db.expire_all()
    assert candidate.start_at == instant and candidate.price_amount == Decimal('123.4567')
    for values in [dict(end_at=datetime(2026, 11, 22, tzinfo=timezone.utc)), dict(price_max=Decimal('1.00'))]:
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(EventCandidate.__table__.update().values(**values))
