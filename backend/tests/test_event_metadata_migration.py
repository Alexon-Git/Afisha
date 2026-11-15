"""Run on SQLite by default; opt in to a throwaway PostgreSQL via test-only URL.

AFISHA_PR6_TEST_DATABASE_URL points ONLY at an isolated test PostgreSQL.
Each test creates/drops its own random schema, never an existing schema.
"""

import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models.event import Event
from app.models.organizer import Organizer
from app.schemas.event import EventCreate, EventUpdate
from app.services.event_service import EventService

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration_database(tmp_path):
    test_url = os.environ.get("AFISHA_PR6_TEST_DATABASE_URL")
    if test_url:
        admin = create_engine(test_url)
        schema = "pr6_" + uuid4().hex
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = make_url(test_url).update_query_dict({"options": f"-csearch_path={schema}"})
        engine = create_engine(url)
    else:
        url = f"sqlite:///{tmp_path / 'metadata.db'}"
        engine = create_engine(url)
    try:
        yield engine, str(url) if isinstance(url, str) else url.render_as_string(hide_password=False)
    finally:
        engine.dispose()
        if test_url:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def upgrade(url, revision):
    env = dict(os.environ, DATABASE_URL=url)
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", revision],
                            cwd=BACKEND, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def assert_schema_matches(engine):
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True})
        assert compare_metadata(context, Base.metadata) == []
        inspector = inspect(connection)
        assert {item["name"] for item in inspector.get_check_constraints("events")} >= {
            "ck_events_publication_status", "ck_events_event_status",
        }
        fk = next(item for item in inspector.get_foreign_keys("events") if item["constrained_columns"] == ["organizer_id"])
        assert fk["referred_table"] == "organizers" and fk["options"]["ondelete"] == "SET NULL"
        assert "ix_events_organizer_id" in {item["name"] for item in inspector.get_indexes("events")}
        columns = {item["name"]: item for item in inspector.get_columns("events")}
        for column in ("organizer_id", "event_url", "source", "verified_at"):
            assert columns[column]["nullable"]
        assert not columns["datetime"]["type"].timezone


def test_fresh_0001_0002_0003_matches_models(migration_database, monkeypatch, tmp_path):
    engine, url = migration_database
    upgrade(url, "head")
    assert_schema_matches(engine)
    upgrade(url, "head")
    monkeypatch.setattr(EventService, "_UPLOAD_DIR", tmp_path / "uploads")
    with Session(engine) as db:
        organizer = Organizer(name="ORM club", description="Optional metadata", public_contact="private-test-contact")
        db.add(organizer)
        db.commit()
        assert organizer.created_at is not None and organizer.updated_at is not None
        service = EventService(db)
        item = service.create_event(EventCreate(title="ORM event", datetime="2026-11-15T12:00:00",
                                               location="NSK", organizer_id=organizer.id,
                                               event_url="https://example.org/event"), creator_id=None)
        assert item.publication_status == "draft" and item.event_status == "scheduled"
        assert item.verified_at is None
        item = service.update_event(item.id, EventUpdate(source="https://example.org/source"))
        assert item.organizer_id == organizer.id and item.verified_at is None
        db.delete(organizer)
        db.commit()
        db.refresh(item)
        assert item.organizer_id is None


def test_0002_upgrade_preserves_all_legacy_data(migration_database):
    engine, url = migration_database
    upgrade(url, "0002_login_attempts")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, username, password_hash, email, is_admin) VALUES (1, 'legacy', 'test-only', 'test@example.org', true)"))
        connection.execute(text("INSERT INTO categories (id, name, slug, is_active) VALUES (1, 'Business', 'business', true)"))
        connection.execute(text("INSERT INTO events (id, title, description, datetime, location, image_url, category_id, creator_id, price, rating, discount, payment_url) VALUES (1, 'Legacy', 'Description', '2026-11-12 23:59:59.123456', 'NSK', '/static/uploads/legacy.png', 1, 1, 1500, 8.5, 10, 'https://example.org/unchecked-payment')"))
        connection.execute(text("INSERT INTO login_attempts VALUES ('account:test-only', 2, 1800000000)"))
        before = {table: connection.execute(text(f"SELECT * FROM {table}")).mappings().all()
                  for table in ("users", "categories", "events", "login_attempts")}
    upgrade(url, "head")
    with engine.begin() as connection:
        for table, original in before.items():
            actual = connection.execute(text(f"SELECT * FROM {table}")).mappings().all()
            assert len(actual) == len(original)
            for old, new in zip(original, actual):
                assert all(new[key] == value for key, value in old.items())
        row = connection.execute(text("SELECT * FROM events WHERE id=1")).mappings().one()
        assert row["publication_status"] == "draft" and row["event_status"] == "scheduled"
        assert all(row[key] is None for key in ("organizer_id", "event_url", "source", "verified_at"))
        connection.execute(text("INSERT INTO events (id, title, datetime, location) VALUES (2, 'New SQL', '2026-12-01 12:00:00', 'NSK')"))
        defaults = connection.execute(text("SELECT publication_status, event_status, verified_at FROM events WHERE id=2")).one()
        assert tuple(defaults) == ("draft", "scheduled", None)
    assert_schema_matches(engine)


def test_db_constraints_and_organizer_deletion(migration_database):
    engine, url = migration_database
    upgrade(url, "head")
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(text("INSERT INTO organizers (id, name) VALUES (1, 'Editorial club')"))
        connection.execute(text("INSERT INTO events (id, title, datetime, location, organizer_id) VALUES (1, 'First', '2026-11-15 12:00:00', 'NSK', 1), (2, 'Second', '2026-11-16 12:00:00', 'NSK', 1)"))
        for publication in ("draft", "published", "archived"):
            for status in ("scheduled", "cancelled", "postponed"):
                connection.execute(text("UPDATE events SET publication_status=:publication, event_status=:status WHERE id=1"),
                                   {"publication": publication, "status": status})
        for sql in (
            "UPDATE events SET publication_status='invalid' WHERE id=1",
            "UPDATE events SET event_status='invalid' WHERE id=1",
            "UPDATE events SET publication_status=NULL WHERE id=1",
            "UPDATE events SET organizer_id=999 WHERE id=1",
        ):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text(sql))
        connection.execute(text("DELETE FROM organizers WHERE id=1"))
        assert connection.execute(text("SELECT count(*) FROM events WHERE organizer_id IS NULL")).scalar_one() == 2
