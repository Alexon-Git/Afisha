"""Explicit instants and empty-only migration, SQLite plus opt-in isolated PG17."""
from datetime import datetime, timezone
import os
import time
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker

from app.auth.auth import get_current_admin_user
from app.database import Base, get_db
from app.main import app
from app.models.event import Event
from app.models.organizer import Organizer
from app.models.user import User
from app.services.event_service import EventService
from test_event_metadata_migration import upgrade

ZONES = ('UTC', 'Asia/Novosibirsk', 'Europe/Moscow', 'America/Los_Angeles')


@pytest.fixture(params=ZONES)
def process_zone(request):
    previous = os.environ.get('TZ')
    os.environ['TZ'] = request.param
    time.tzset()
    try:
        yield request.param
    finally:
        if previous is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = previous
        time.tzset()


@pytest.fixture(params=['sqlite', 'postgresql'])
def time_database(request, tmp_path, process_zone):
    if request.param == 'sqlite':
        url = f"sqlite:///{tmp_path / 'time.db'}"
    else:
        value = os.environ.get('AFISHA_PR8_TEST_DATABASE_URL')
        if not value:
            pytest.skip('Isolated PostgreSQL opt-in URL not supplied')
        base_url = make_url(value)
        if base_url.host not in {'pr8db', '127.0.0.1'} or (base_url.database, base_url.username) != ('afisha_pr8', 'pr8_test'):
            pytest.fail('PR-8 tests require the designated isolated PostgreSQL')
        admin = create_engine(base_url)
        schema = 'pr8_' + uuid4().hex
        with admin.begin() as connection:
            assert connection.execute(text('SHOW server_version_num')).scalar().startswith('17')
            connection.execute(text(f'CREATE SCHEMA {schema}'))
        admin.dispose()
        url = base_url.update_query_dict({'options': f'-csearch_path={schema} -cTimeZone={process_zone}'})
        url = url.render_as_string(hide_password=False)
    engine = create_engine(url)
    try:
        yield engine, url
    finally:
        engine.dispose()  # Isolated test schemas retained; no database/volume deletion.


def test_empty_migration_and_http_contract(time_database, tmp_path, monkeypatch):
    engine, url = time_database
    upgrade(url, '0003_event_metadata')
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id,username,password_hash,is_admin) VALUES (1,'fixture','not-real',true)"))
        connection.execute(text("INSERT INTO categories (id,name,slug,is_active) VALUES (1,'Fixture','fixture',true)"))
    upgrade(url, 'head')
    upgrade(url, 'head')
    with engine.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar() == '0008_event_pricing'
        assert connection.execute(text('SELECT count(*) FROM users')).scalar() == 1
        assert connection.execute(text('SELECT count(*) FROM categories')).scalar() == 1
        assert next(c for c in inspect(connection).get_columns('events') if c['name'] == 'datetime')['type'].timezone == (engine.dialect.name == 'postgresql')
        assert compare_metadata(MigrationContext.configure(connection, opts={'compare_type': True}), Base.metadata) == []
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add(Organizer(id=1, name='Fixture club', public_contact='Public fixture'))
    old_overrides = app.dependency_overrides.copy()

    def database():
        with sessions() as db:
            yield db

    monkeypatch.setattr(EventService, '_UPLOAD_DIR', tmp_path / 'uploads')
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_admin_user] = lambda: User(id=1, is_admin=True)
    try:
        with TestClient(app) as client:
            payload = dict(title='Absolute event', datetime='2026-11-12T00:00:00+07:00', location='Novosibirsk',
                           organizer_id=1, event_url='https://example.org/event', source='https://example.org/source')
            response = client.post('/events/', json=payload)
            assert response.status_code == 200, response.text
            item = response.json()
            identifier = item['id']
            instant = datetime(2026, 11, 11, 17, tzinfo=timezone.utc)
            assert datetime.fromisoformat(item['datetime']) == instant
            assert item['verified_at'] is None and item['publication_status'] == 'draft'
            assert client.get(f'/events/{identifier}').status_code == 404
            for bad in ['2026-11-12T00:00:00', '2026-11-12', 1794416400, '1794416400']:
                assert client.post('/events/', json={**payload, 'datetime': bad}).status_code == 422
                assert client.put(f'/events/{identifier}', json={'datetime': bad}).status_code == 422
            for action, body in [('status', {'event_status': 'cancelled'}), ('status', {'event_status': 'postponed'}),
                                 ('verify', None), ('publication', {'publication_status': 'published'})]:
                response = client.post(f'/admin/events/{identifier}/{action}') if body is None else client.patch(f'/admin/events/{identifier}/{action}', json=body)
                assert response.status_code == 200, response.text
                assert datetime.fromisoformat(response.json()['datetime']) == instant
            assert client.get(f'/events/{identifier}').status_code == 200
            # Same instant with a different offset is not a critical change.
            response = client.put(f'/events/{identifier}', json={'datetime': '2026-11-11T09:00:00-08:00', 'description': 'Edited'})
            assert response.status_code == 200, response.text
            assert datetime.fromisoformat(response.json()['datetime']) == instant
            assert client.put(f'/events/{identifier}', json={'datetime': '2026-11-12T01:00:00+07:00'}).status_code == 422
            for title, moment in [('Before', '2026-11-11T23:59:59.999999+07:00'), ('Next', '2026-11-13T00:00:00+07:00'), ('Weekend', '2026-11-14T00:00:00+07:00'), ('Monday', '2026-11-16T00:00:00+07:00')]:
                with sessions.begin() as db:
                    db.add(Event(title=title, datetime=datetime.fromisoformat(moment), location='NSK', publication_status='published'))
            for params in [{'date': '2026-11-12'}, {'date_from': '2026-11-12', 'date_to': '2026-11-12'}]:
                response = client.get('/events/', params=params)
                assert response.status_code == 200
                assert [i['id'] for i in response.json()['items']] == [identifier]
            assert [i['title'] for i in client.get('/events/', params={'sort': 'asc'}).json()['items']] == ['Before', 'Absolute event', 'Next', 'Weekend', 'Monday']
            assert [i['title'] for i in client.get('/events/', params={'sort': 'desc'}).json()['items']] == ['Monday', 'Weekend', 'Next', 'Absolute event', 'Before']
            from app.services import event_service as event_module
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    fixed = datetime(2026, 11, 11, 18, tzinfo=timezone.utc)
                    return fixed.astimezone(tz) if tz else fixed.astimezone().replace(tzinfo=None)
            with monkeypatch.context() as clock_patch:
                clock_patch.setattr(event_module, 'datetime', Clock)
                for selector, titles in [('today', ['Absolute event']), ('tomorrow', ['Next']), ('weekend', ['Weekend'])]:
                    response = client.get('/events/', params={'date': selector})
                    assert response.status_code == 200, response.text
                    assert [i['title'] for i in response.json()['items']] == titles
            assert client.patch(f'/admin/events/{identifier}/publication', json={'publication_status': 'draft'}).status_code == 200
            changed = client.put(f'/events/{identifier}', json={'datetime': '2026-11-13T12:00:00+07:00'})
            assert changed.status_code == 200 and changed.json()['verified_at'] is None
            assert datetime.fromisoformat(changed.json()['datetime']) == datetime(2026,11,13,5,tzinfo=timezone.utc)
            with sessions() as db:
                assert db.get(Event, identifier).datetime == datetime(2026,11,13,5,tzinfo=timezone.utc)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)
    # ORM writes cannot silently interpret naive values either.
    with sessions() as db:
        db.add(Event(title='Bad ORM', datetime=datetime(2026,11,12), location='NSK'))
        with pytest.raises(StatementError, match='explicit UTC offset'):
            db.commit()


def test_populated_migration_refuses_without_changes(time_database):
    engine, url = time_database
    upgrade(url, '0003_event_metadata')
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO events (title,datetime,location) VALUES ('Historical','2026-11-12 12:34:56.123456','NSK')"))
        before = connection.execute(text('SELECT * FROM events')).mappings().all()
    import subprocess
    import sys
    from pathlib import Path
    result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'],
                            cwd=Path(__file__).resolve().parents[1], env=dict(os.environ, DATABASE_URL=url), capture_output=True, text=True)
    assert result.returncode != 0 and 'existing event datetimes' in result.stderr
    with engine.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar() == '0003_event_metadata'
        assert connection.execute(text('SELECT * FROM events')).mappings().all() == before
        assert not next(c for c in inspect(connection).get_columns('events') if c['name']=='datetime')['type'].timezone


INVALID_INSTANTS = (
    '9999-12-31T23:59:59Z',
    '0001-01-01T00:00:00Z',
    '1899-12-31T23:59:59.999999Z',
    '2101-01-01T00:00:00Z',
    '1900-01-01T00:00:00+07:00',  # Wall-clock year alone would falsely allow it.
    '2100-12-31T23:59:59.999999-08:00',
)
VALID_INSTANTS = (
    '2026-11-23T12:00:00+07:00',
    '1900-01-01T00:00:00Z',
    '2100-12-31T23:59:59.999999Z',
    '1899-12-31T16:00:00-08:00',  # Local year outside the range, instant on bound.
    '2101-01-01T06:59:59.999999+07:00',
)


def test_date_range_rejects_before_writes_and_preserves_readability(time_database, tmp_path, monkeypatch):
    engine, url = time_database
    upgrade(url, 'head')
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add(User(id=1, username='range-admin', password_hash='test-only', is_admin=True))
    with engine.connect() as connection:
        if engine.dialect.name == 'postgresql':
            assert connection.execute(text('SHOW TimeZone')).scalar() == os.environ['TZ']
    previous = app.dependency_overrides.copy()

    def database():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_admin_user] = lambda: User(id=1, is_admin=True)
    monkeypatch.setattr(EventService, '_UPLOAD_DIR', tmp_path / 'uploads')
    payload = dict(title='Preserved', description='Original', datetime=VALID_INSTANTS[0], location='Novosibirsk')

    def stored_rows():
        with engine.connect() as connection:
            return connection.execute(text('SELECT * FROM events ORDER BY id')).mappings().all()

    try:
        with TestClient(app) as client:
            created = client.post('/events/', json=payload)
            assert created.status_code == 200, created.text
            identifier = created.json()['id']
            for bad in INVALID_INSTANTS:
                before = stored_rows()
                response = client.post('/events/', json={**payload, 'title': 'Must not exist', 'datetime': bad})
                assert response.status_code == 422, response.text
                assert stored_rows() == before  # No committed row, not just an error response.
                response = client.put(f'/events/{identifier}', json={
                    'datetime': bad, 'title': 'Must not change', 'description': 'Changed', 'location': 'Elsewhere'})
                assert response.status_code == 422, response.text
                assert stored_rows() == before  # All fields are unchanged, not only datetime.
                listing = client.get('/admin/events/')
                assert listing.status_code == 200, listing.text
                assert listing.json()['total_items'] == len(before)
                assert client.get(f'/admin/events/{identifier}').status_code == 200
                # Neither rejection poisons subsequent sessions/transactions.
                assert client.post('/events/', json=payload).status_code == 200
                assert client.put(f'/events/{identifier}', json={'datetime': VALID_INSTANTS[0]}).status_code == 200
            for good in VALID_INSTANTS:
                expected = datetime.fromisoformat(good).astimezone(timezone.utc)
                for response in (client.post('/events/', json={**payload, 'datetime': good}),
                                 client.put(f'/events/{identifier}', json={'datetime': good})):
                    assert response.status_code == 200, response.text
                    assert response.json()['datetime'].endswith('Z')
                    assert datetime.fromisoformat(response.json()['datetime']) == expected
                fetched = client.get(f'/admin/events/{identifier}')
                assert fetched.status_code == 200
                assert datetime.fromisoformat(fetched.json()['datetime']) == expected
            # Last writable instant belongs to 2101-01-01 in Novosibirsk. Query
            # bounds outside the write range must not reject valid stored events.
            for params in ({'date': '2101-01-01'}, {'date_from': '2101-01-01', 'date_to': '2101-01-01'}):
                response = client.get('/admin/events/', params=params)
                assert response.status_code == 200, response.text
                assert identifier in [item['id'] for item in response.json()['items']]
            with sessions() as db:
                original = db.get(Event, identifier).datetime
            for bad in INVALID_INSTANTS:
                before = stored_rows()
                with sessions() as db:
                    db.add(Event(title='Rejected ORM', datetime=datetime.fromisoformat(bad), location='NSK'))
                    with pytest.raises(StatementError, match='1900-01-01'):
                        db.commit()
                    db.rollback()
                    item = db.get(Event, identifier)
                    item.datetime = datetime.fromisoformat(bad)
                    item.title = 'Rejected ORM update'
                    with pytest.raises(StatementError, match='1900-01-01'):
                        db.commit()
                    db.rollback()
                    assert db.get(Event, identifier).datetime == original
                assert stored_rows() == before
            assert client.get('/admin/events/').status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
