"""SQLite/opt-in PostgreSQL regression for stale ORM state and publication races."""
from datetime import datetime, timezone
import threading

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.organizer import Organizer
from app.models.event_status import PublicationStatus
from app.schemas.event import EventUpdate
from app.services.event_service import EventService
from app.services.exceptions import PublicationValidationError
from test_event_metadata_migration import migration_database, upgrade

def test_edit_and_publication_serialize_and_refresh_stale_state(migration_database, tmp_path, monkeypatch):
    engine, url = migration_database
    assert engine.dialect.name in ("sqlite", "postgresql")
    upgrade(url, "head")
    monkeypatch.setattr(EventService, "_UPLOAD_DIR", tmp_path / "uploads")
    with Session(engine) as db:
        db.add(Organizer(id=1, name="Club", public_contact="Designated public contact"))
        db.flush()
        db.add(Event(id=1, title="Event", datetime=datetime(2026, 11, 15, tzinfo=timezone.utc), location="Old place",
                     organizer_id=1, event_url="https://example.org/event", source="https://example.org/source",
                     verified_at=datetime(2026, 11, 15, tzinfo=timezone.utc)))
        db.commit()
    warmed, pending, attempted, release, finished = [threading.Event() for _ in range(5)]
    failures, rejected = [], []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if threading.current_thread().name == "pr7-publisher" and ("FOR UPDATE" in statement or "BEGIN IMMEDIATE" in statement):
            attempted.set()

    event.listen(engine, "before_cursor_execute", observe)

    def publisher():
        try:
            with Session(engine) as db:
                cached = db.get(Event, 1)  # Intentionally retain a stale, verified identity-map object.
                warmed.set()
                assert pending.wait(10)
                try:
                    EventService(db).change_publication(1, PublicationStatus.PUBLISHED)
                except PublicationValidationError as exc:
                    rejected.append(exc.fields)
                assert cached.verified_at is None
        except Exception as exc:
            failures.append(exc)
        finally:
            finished.set()

    def writer():
        try:
            assert warmed.wait(10)
            with Session(engine) as db:
                commit = db.commit

                def pause_commit():
                    pending.set()
                    assert release.wait(10)
                    commit()

                db.commit = pause_commit
                EventService(db).update_event(1, EventUpdate(location="New place"))
        except Exception as exc:
            failures.append(exc)

    threads = [threading.Thread(target=publisher, name="pr7-publisher", daemon=True),
               threading.Thread(target=writer, name="pr7-writer", daemon=True)]
    for thread in threads:
        thread.start()
    try:
        assert attempted.wait(10)
        assert not finished.wait(0.1), "Publication bypassed the event row lock"
    finally:
        release.set()
        for thread in threads:
            thread.join(10)
        event.remove(engine, "before_cursor_execute", observe)
    assert all(not thread.is_alive() for thread in threads) and not failures
    assert len(rejected) == 1 and "verified_at" in rejected[0]
    with Session(engine) as db:
        item = db.get(Event, 1)
        assert item.publication_status == "draft" and item.verified_at is None
        assert item.location == "New place"
