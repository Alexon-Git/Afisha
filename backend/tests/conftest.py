"""Disposable event-editing storage; all files and data stay in pytest tmp_path."""

from datetime import datetime
import socket
import threading
import time

from fastapi.testclient import TestClient
import pytest
import httpx
import uvicorn
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.auth.auth import get_current_admin_user
from app.database import Base, get_db
from app.main import app
from app.models.category import Category
from app.models.event import Event
from app.models.user import User
from app.services.event_service import EventService


@pytest.fixture
def event_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(EventService, "_UPLOAD_DIR", tmp_path / "uploads")
    engine = create_engine(f"sqlite:///{tmp_path / 'events.db'}")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add(User(id=1, username="test-admin", password_hash="test-only", is_admin=True))
        db.add(Category(id=1, name="Business", slug="business"))
        db.flush()
        db.add(Event(id=1, title="Original", datetime=datetime(2026, 11, 15, 12),
                     location="Novosibirsk", category_id=1, creator_id=1))
    try:
        yield sessions
    finally:
        engine.dispose()


@pytest.fixture
def event_api(event_sessions):
    previous = app.dependency_overrides.copy()

    def db_session():
        with event_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = db_session
    app.dependency_overrides[get_current_admin_user] = lambda: User(id=1, is_admin=True)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def live_event_api(event_api):
    """Same isolated API over a real loopback TCP connection."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off", proxy_headers=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with httpx.Client(base_url=f"http://127.0.0.1:{sock.getsockname()[1]}", timeout=5) as client:
                yield client
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive()
