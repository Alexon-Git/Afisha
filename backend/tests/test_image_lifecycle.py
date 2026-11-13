"""Image cleanup never touches real uploads and happens only after commit."""

from datetime import datetime
from pathlib import Path
import threading

import pytest
from sqlalchemy.exc import OperationalError

from app.models.event import Event
from app.schemas.event import EventUpdate
from app.services import event_service as module
from app.services.event_service import EventService
from app.services.exceptions import InvalidImageError


OLD = "/static/uploads/" + "a" * 32 + ".png"
NEW = "/static/uploads/" + "b" * 32 + ".jpg"


def attach(sessions, url=OLD, shared=False):
    uploads = EventService._UPLOAD_DIR
    uploads.mkdir(exist_ok=True)
    file = uploads / Path(OLD).name
    file.write_bytes(b"test-only-image")
    (uploads / Path(NEW).name).write_bytes(b"new-test-image")
    with sessions.begin() as db:
        db.get(Event, 1).image_url = url
        if shared:
            db.add(Event(id=2, title="Shared", datetime=datetime(2026, 11, 16),
                         location="Novosibirsk", image_url=url))
    return file


def test_delete_removes_file_after_successful_commit(event_api, event_sessions, monkeypatch):
    file = attach(event_sessions)
    remove = EventService._remove_image

    def verify_committed(service, url):
        with event_sessions() as db:
            assert db.get(Event, 1) is None
        remove(service, url)

    monkeypatch.setattr(EventService, "_remove_image", verify_committed)
    assert event_api.delete("/events/1").status_code == 200
    assert not file.exists()
    assert event_api.get("/events/1").status_code == 404


@pytest.mark.parametrize("action", ["delete", "replace", "clear"])
def test_shared_image_is_retained(event_api, event_sessions, action):
    file = attach(event_sessions, shared=True)
    if action == "delete":
        response = event_api.delete("/events/1")
    else:
        response = event_api.put("/events/1", json={"image_url": NEW if action == "replace" else None})
    assert response.status_code == 200
    assert file.read_bytes() == b"test-only-image"
    assert event_api.get("/events/2").json()["image_url"] == OLD
    assert event_api.delete("/events/2").status_code == 200
    assert not file.exists()


@pytest.mark.parametrize("replacement", [NEW, None, ""])
def test_replace_or_clear_cleans_only_old_image(event_api, event_sessions, replacement):
    file = attach(event_sessions)
    new_file = EventService._UPLOAD_DIR / Path(NEW).name
    new_file.write_bytes(b"new-test-image")
    response = event_api.put("/events/1", json={"image_url": replacement})
    assert response.status_code == 200
    assert response.json()["image_url"] == replacement
    assert not file.exists()
    assert new_file.read_bytes() == b"new-test-image"


def test_unchanged_image_is_retained(event_api, event_sessions):
    file = attach(event_sessions)
    assert event_api.put("/events/1", json={"title": "Changed", "image_url": OLD}).status_code == 200
    assert file.exists()


@pytest.mark.parametrize("action", ["delete", "update"])
def test_commit_failure_keeps_file_and_record(event_sessions, monkeypatch, action):
    file = attach(event_sessions)
    with event_sessions() as db:
        service = EventService(db)

        def fail():
            raise OperationalError("test commit", {}, RuntimeError("test-only failure"))

        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(OperationalError):
            if action == "delete":
                service.delete_event(1)
            else:
                service.update_event(1, EventUpdate(image_url=NEW))
        db.rollback()
    assert file.exists()
    with event_sessions() as db:
        assert db.get(Event, 1).image_url == OLD


@pytest.mark.parametrize("action", ["delete", "update"])
def test_unlink_failure_does_not_report_failed_mutation(event_api, event_sessions, monkeypatch, action):
    file = attach(event_sessions)
    original_unlink = Path.unlink

    def fail(path, *args, **kwargs):
        if path == file:
            raise PermissionError("test-only unlink denied")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail)
    response = event_api.delete("/events/1") if action == "delete" else event_api.put("/events/1", json={"image_url": NEW})
    assert response.status_code == 200
    assert file.exists()
    if action == "delete":
        assert event_api.get("/events/1").status_code == 404
    else:
        assert event_api.get("/events/1").json()["image_url"] == NEW


@pytest.mark.parametrize("url", [
    "https://example.org" + OLD, "//example.org" + OLD, "/tmp/" + Path(OLD).name,
    "/static/uploads/../" + Path(OLD).name, OLD + "?v=1", OLD.replace("/uploads/", "/uploads/%2e%2e/"),
    "/static/uploads/legacy.png",
])
def test_external_and_unowned_paths_are_not_cleaned(event_api, event_sessions, url):
    file = attach(event_sessions, url=url)
    assert event_api.delete("/events/1").status_code == 200
    assert file.exists()


def test_symlink_and_target_are_retained(event_api, event_sessions, tmp_path):
    file = attach(event_sessions)
    target = tmp_path / "outside-uploads.png"
    target.write_bytes(b"keep-me")
    file.unlink()
    file.symlink_to(target)
    assert event_api.delete("/events/1").status_code == 200
    assert file.is_symlink() and target.read_bytes() == b"keep-me"


def test_failed_reference_lookup_defers_cleanup(event_api, event_sessions, monkeypatch):
    file = attach(event_sessions)

    def fail(*args, **kwargs):
        raise OperationalError("test lookup", {}, RuntimeError("test-only failure"))

    monkeypatch.setattr(module, "Session", fail)
    assert event_api.delete("/events/1").status_code == 200
    assert file.exists()


def test_missing_owned_image_returns_422_without_changes(event_api):
    before = event_api.get("/events/1").json()
    assert event_api.put("/events/1", json={"title": "Not saved", "image_url": OLD}).status_code == 422
    assert event_api.post("/events/", json={"title": "New", "datetime": "2026-11-15T12:00:00",
                                          "location": "Novosibirsk", "image_url": OLD}).status_code == 422
    assert event_api.get("/events/1").json() == before


def test_committing_reference_prevents_cleanup(event_api, event_sessions):
    file = attach(event_sessions)
    locked, release = threading.Event(), threading.Event()
    failures = []

    def writer():
        try:
            with event_sessions() as db:
                service = EventService(db)
                with service._image_reference(OLD):
                    locked.set()
                    assert release.wait(5)
                    db.add(Event(id=2, title="Concurrent", datetime=datetime(2026, 11, 16),
                                 location="Novosibirsk", image_url=OLD))
                    db.commit()
        except Exception as exc:
            failures.append(exc)

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    try:
        assert locked.wait(5)
        assert event_api.delete("/events/1").status_code == 200
        assert file.exists()
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive() and not failures
    assert event_api.get("/events/2").json()["image_url"] == OLD
    assert file.exists()


def test_reference_opened_before_unlink_cannot_commit_after_unlink(event_sessions, monkeypatch):
    file = attach(event_sessions)
    attempting = threading.Event()
    failures = []
    flock = module.fcntl.flock

    def observe(fd, operation):
        if operation == module.fcntl.LOCK_SH:
            attempting.set()
        return flock(fd, operation)

    monkeypatch.setattr(module.fcntl, "flock", observe)

    def writer():
        try:
            with event_sessions() as db:
                EventService(db).update_event(1, EventUpdate(image_url=NEW))
        except Exception as exc:
            failures.append(exc)

    # Cleanup has the exclusive inode lock before a new reference opens it.
    new_file = file.parent / Path(NEW).name
    with new_file.open("rb") as image:
        flock(image, module.fcntl.LOCK_EX)
        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        try:
            assert attempting.wait(5)
            new_file.unlink()
        finally:
            flock(image, module.fcntl.LOCK_UN)
    thread.join(5)
    assert not thread.is_alive()
    assert len(failures) == 1 and isinstance(failures[0], InvalidImageError)
    with event_sessions() as db:
        assert db.get(Event, 1).image_url == OLD
