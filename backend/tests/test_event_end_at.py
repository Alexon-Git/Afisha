"""End-to-end period contract on isolated SQLite and PostgreSQL 17 schemas."""
from datetime import datetime, timezone

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, select, text, func
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker

from app.auth.auth import get_current_admin_user
from app.database import Base, get_db
from app.main import app
from app.models import Event, User, Organizer
from app.services.event_service import EventService
from test_event_metadata_migration import upgrade
from test_event_time_contract import time_database, process_zone

START = '2026-11-26T10:00:00+07:00'
END = '2026-11-28T18:00:00+07:00'


def test_migration_and_period_http_contract(time_database, monkeypatch, tmp_path):
    engine, url = time_database
    upgrade(url, '0006_import_worker_integrity')
    with engine.begin() as db:
        db.execute(text("INSERT INTO users (id,username,password_hash,is_admin) VALUES (1,'fixture','not-real',true)"))
        db.execute(text("INSERT INTO categories (id,name,slug,is_active) VALUES (1,'Fixture','fixture',true)"))
        db.execute(text("INSERT INTO events (id,title,datetime,location) VALUES (1,'Legacy','2026-11-26 03:00:00+00:00','NSK')"))
        before = dict(db.execute(text('SELECT * FROM events WHERE id=1')).mappings().one())
    upgrade(url, 'head')
    upgrade(url, 'head')
    with engine.connect() as db:
        row = dict(db.execute(text('SELECT * FROM events WHERE id=1')).mappings().one())
        assert row.pop('end_at') is None
        assert row == before
        assert db.execute(text('SELECT count(*) FROM users')).scalar() == 1
        assert db.execute(text('SELECT count(*) FROM categories')).scalar() == 1
        column = next(c for c in inspect(db).get_columns('events') if c['name'] == 'end_at')
        assert column['nullable']
        assert column['type'].timezone == (engine.dialect.name == 'postgresql')
        assert compare_metadata(MigrationContext.configure(db, opts={'compare_type': True}), Base.metadata) == []
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add(Organizer(id=1, name='Synthetic', public_contact='Synthetic public contact'))
        if engine.dialect.name == 'postgresql':
            db.execute(text("SELECT setval(pg_get_serial_sequence('events','id'),1)"))
    previous = app.dependency_overrides.copy()
    def database():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_admin_user] = lambda: User(id=1, is_admin=True)
    monkeypatch.setattr(EventService, '_UPLOAD_DIR', tmp_path / 'uploads')
    payload = dict(title='Period', datetime=START, end_at=END, location='NSK', organizer_id=1,
                   category_id=1, event_url='https://example.invalid/event', source='https://example.invalid/source')
    try:
        with TestClient(app) as client:
            # Old clients can omit the field. All rejected writes are atomic.
            old = client.post('/events/', json={k:v for k,v in payload.items() if k != 'end_at'})
            assert old.status_code == 200 and old.json()['end_at'] is None
            with sessions() as db:
                count = db.scalar(select(func.count()).select_from(Event))
            for bad in [START, '2026-11-25T12:00:00Z', '2026-11-28T18:00:00',
                        '9999-12-31T23:59:59Z', '0001-01-01T00:00:00Z']:
                assert client.post('/events/', json={**payload, 'end_at': bad}).status_code == 422
            with sessions() as db:
                assert db.scalar(select(func.count()).select_from(Event)) == count
            response = client.post('/events/', json=payload)
            assert response.status_code == 200, response.text
            eid = response.json()['id']
            assert response.json()['end_at'] == '2026-11-28T11:00:00Z'
            path = f'/events/{eid}'
            for patch in [{'datetime': END, 'title':'Invalid'}, {'end_at': START, 'title':'Invalid'},
                          {'end_at': '2026-11-28T18:00:00'}, {'end_at':'2101-01-01T00:00:00Z'}]:
                assert client.put(path, json=patch).status_code == 422
                with sessions() as db:
                    stored = db.get(Event, eid)
                    assert stored.title == 'Period' and stored.end_at.isoformat() == '2026-11-28T11:00:00+00:00'
                    assert stored.datetime.isoformat() == '2026-11-26T03:00:00+00:00'
            assert client.put(path, json={'description':'Safe'}).json()['end_at'] == '2026-11-28T11:00:00Z'
            # Changing only start/end and explicit clearing/replacement.
            assert client.put(path, json={'datetime':'2026-11-25T10:00:00+07:00'}).status_code == 200
            assert client.put(path, json={'end_at':None}).json()['end_at'] is None
            assert client.put(path, json={'datetime':START,'end_at':END}).status_code == 200
            assert client.post(f'/admin/events/{eid}/verify').status_code == 200
            assert client.patch(f'/admin/events/{eid}/publication', json={'publication_status':'published'}).status_code == 200
            assert client.put(path, json={'end_at':'2026-11-29T18:00:00+07:00'}).status_code == 422
            assert client.get(path).json()['end_at'] == '2026-11-28T11:00:00Z'
            assert client.patch(f'/admin/events/{eid}/publication', json={'publication_status':'draft'}).status_code == 200
            edited = client.put(path, json={'end_at':'2026-11-29T00:00:00+07:00'})
            assert edited.status_code == 200 and edited.json()['verified_at'] is None
            assert client.patch(f'/admin/events/{eid}/publication', json={'publication_status':'published'}).status_code == 422
            assert client.post(f'/admin/events/{eid}/verify').status_code == 200
            assert client.patch(f'/admin/events/{eid}/publication', json={'publication_status':'published'}).status_code == 200
            for day, expected in [('2026-11-25',0), ('2026-11-26',1), ('2026-11-27',1), ('2026-11-28',1), ('2026-11-29',0)]:
                result = client.get('/events/', params={'date':day}).json()
                assert result['total_items'] == expected, (day,result)
            result = client.get('/events/', params={'date_from':'2026-11-27','date_to':'2026-11-28','category':'fixture','limit':1,'sort':'desc'}).json()
            assert result['total_items'] == 1 and result['total_pages'] == 1
            assert result['items'][0]['id'] == eid
            assert client.get('/admin/events/').status_code == 200
            # A normal post/update still works after all validation failures.
            assert client.post('/events/', json=payload).status_code == 200
            assert client.put(path, json={'description':'Still safe'}).status_code == 200
        # Bypassing Pydantic still cannot write an unsupported/naive end instant.
        for bad in [datetime(2026,11,28), datetime(9999,12,31,tzinfo=timezone.utc)]:
            with sessions() as db:
                db.add(Event(title='Invalid ORM', datetime=datetime(2026,11,26,tzinfo=timezone.utc), end_at=bad, location='NSK'))
                with pytest.raises(StatementError):
                    db.commit()
                db.rollback()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_overlap_boundaries_relative_filters_and_points(event_sessions, monkeypatch):
    from app.services import event_service as module
    from app.schemas.event import EventCreate
    from datetime import timedelta
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026,11,27,5,tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(module, 'datetime', Clock)
    with event_sessions() as db:
        service = EventService(db)
        for title, start, end in [
            ('ongoing','2026-11-26T10:00:00+07:00',END),
            ('ends_at_lower','2026-11-26T10:00:00+07:00','2026-11-27T00:00:00+07:00'),
            ('point_at_lower','2026-11-27T00:00:00+07:00',None),
            ('point_before','2026-11-26T23:59:59.999999+07:00',None),
            ('starts_at_upper','2026-11-28T00:00:00+07:00',None),
            ('crosses_midnight','2026-11-26T23:30:00+07:00','2026-11-27T00:30:00+07:00'),
        ]:
            e = service.create_event(EventCreate(title=title, datetime=start, end_at=end, location='NSK'), creator_id=1)
            e.publication_status='published'
            db.commit()
        for query in [{'date':'today'},{'date':'2026-11-27'},{'date_from':'2026-11-27'}, {'date_to':'2026-11-27'}]:
            result = service.list_events(**query)
            assert [e.title for e in result['items']] == ['ongoing','crosses_midnight','point_at_lower']
            assert result['total_items'] == 3
        assert [e.title for e in service.list_events(date='tomorrow')['items']] == ['ongoing','starts_at_upper']
        assert [e.title for e in service.list_events(date='weekend')['items']] == ['ongoing','starts_at_upper']
        first=service.list_events(date='today', limit=2, page=1, sort='desc')
        second=service.list_events(date='today', limit=2, page=2, sort='desc')
        assert first['total_items']==second['total_items']==3
        assert len({e.id for e in first['items']+second['items']})==3
