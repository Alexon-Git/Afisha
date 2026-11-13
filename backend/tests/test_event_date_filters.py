"""Calendar filters on disposable SQLite data; no production database access."""

from datetime import datetime
import os
import socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import urlopen
import json

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uvicorn

from app.database import Base
from app.dependencies import get_event_service
from app.main import app
from app.models.category import Category
from app.models.event import Event
from app.services import event_service as module
from app.services.event_service import EventService
from app.services.exceptions import InvalidDateFilterError


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(EventService, "_UPLOAD_DIR", tmp_path / "uploads")
    engine = create_engine(f"sqlite:///{tmp_path / 'events.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        category = Category(name="Business", slug="business")
        other = Category(name="Other", slug="other")
        db.add_all([category, other])
        db.flush()
        for title, moment, group in [
            ("before", "2026-11-11T23:59:59.999999", category),
            ("start", "2026-11-12T00:00:00", category),
            ("other", "2026-11-12T12:00:00", other),
            ("late", "2026-11-12T23:59:59", category),
            ("micro", "2026-11-12T23:59:59.999999", category),
            ("next", "2026-11-13T00:00:00", category),
            ("second-end", "2026-11-13T23:59:59.999999", category),
            ("after", "2026-11-14T00:00:00", category),
            ("year-end", "2026-12-31T23:59:59.999999", category),
            ("new-year", "2027-01-01T00:00:00", category),
            ("year-after", "2027-01-02T00:00:00", category),
        ]:
            db.add(Event(title=title, datetime=datetime.fromisoformat(moment),
                         location="Novosibirsk", category_id=group.id))
    try:
        yield sessions
    finally:
        engine.dispose()


@pytest.fixture
def api(catalog):
    previous = app.dependency_overrides.copy()

    def service():
        with catalog() as db:
            yield EventService(db)

    app.dependency_overrides[get_event_service] = service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.parametrize("params", [
    {"date": "2026-11-12"},
    {"date_from": "2026-11-12", "date_to": "2026-11-12"},
    {"date_from": "2026-11-12"},
    {"date_to": "2026-11-12"},
    {"date": "ignored", "date_from": "2026-11-12"},
])
def test_single_day_boundaries(api, params):
    response = api.get("/events/", params=params)
    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["start", "other", "late", "micro"]
    assert body["total_items"] == 4
    assert body["items"][0]["datetime"] == "2026-11-12T00:00:00"
    assert body["items"][-1]["datetime"] == "2026-11-12T23:59:59.999999"


def test_multiple_days(api):
    response = api.get("/events/", params={"date_from": "2026-11-12", "date_to": "2026-11-13"})
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == [
        "start", "other", "late", "micro", "next", "second-end",
    ]


def test_year_and_month_boundary(api):
    response = api.get("/events/", params={"date_from": "2026-12-31", "date_to": "2027-01-01"})
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["year-end", "new-year"]


BAD_FILTERS = [
    {"date": value} for value in [
        "", "unknown", "2026-13-01", "2026-00-01", "2026-11-32", "2026-02-29",
        "2026-2-01", "2026-02-1", "26-02-01", "2026/02/01", "2026-11-12T00:00:00",
        " 2026-11-12", "2026-11-12\n", "２０２６-１１-１２", "0000-01-01", "10000-01-01",
        "9999-12-31",
    ]
] + [
    {"date_from": "2026-11-13", "date_to": "2026-11-12"},
    {"date_from": ""}, {"date_to": ""},
    {"date_from": "2026-11-12", "date_to": ""},
    {"date_from": "2026-02-30"}, {"date_to": "bad"},
    {"date_from": "9999-12-30", "date_to": "9999-12-31"},
]


@pytest.mark.parametrize("params", BAD_FILTERS)
def test_invalid_filters_raise_in_service_and_return_400(api, catalog, params):
    with catalog() as db, pytest.raises(InvalidDateFilterError):
        EventService(db).list_events(**params, category="unknown")
    for category in ("business", "unknown"):
        response = api.get("/events/", params={**params, "category": category})
        assert response.status_code == 400
        assert set(response.json()) == {"detail"}
        assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("value,end", [
    ("0001-01-01", datetime(1, 1, 2)),
    ("9999-12-30", datetime(9999, 12, 31)),
    ("2028-02-29", datetime(2028, 3, 1)),
])
def test_valid_extreme_and_leap_dates(api, value, end):
    start, actual_end = EventService(None)._resolve_date_filters(date=value, date_from=None, date_to=None)
    assert start == datetime.fromisoformat(value)
    assert actual_end == end
    assert start.tzinfo is actual_end.tzinfo is None
    assert api.get("/events/", params={"date": value}).status_code == 200


@pytest.mark.parametrize("server_tz", ["UTC", "Asia/Novosibirsk", "Europe/Moscow", "America/Los_Angeles"])
@pytest.mark.parametrize("instant,selector,start,end", [
    ("2026-11-11T18:00:00+00:00", "today", "2026-11-12", "2026-11-13"),
    ("2026-12-31T18:00:00+00:00", "today", "2027-01-01", "2027-01-02"),
    ("2026-12-30T18:00:00+00:00", "tomorrow", "2027-01-01", "2027-01-02"),
    ("2026-11-13T18:00:00+00:00", "weekend", "2026-11-14", "2026-11-16"),
    ("2026-11-14T18:00:00+00:00", "weekend", "2026-11-14", "2026-11-16"),
    ("2026-11-15T18:00:00+00:00", "weekend", "2026-11-21", "2026-11-23"),
])
def test_relative_dates_ignore_server_timezone(api, monkeypatch, server_tz, instant, selector, start, end):
    fixed = datetime.fromisoformat(instant)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            # Without an explicit zone this follows the real process TZ.
            return fixed.astimezone(tz) if tz else datetime.fromtimestamp(fixed.timestamp())

    original_tz = os.environ.get("TZ")
    monkeypatch.setenv("TZ", server_tz)
    time.tzset()
    monkeypatch.setattr(module, "datetime", Clock)
    try:
        bounds = EventService(None)._resolve_date_filters(date=selector, date_from=None, date_to=None)
        assert bounds == (datetime.fromisoformat(start), datetime.fromisoformat(end))
        assert all(bound.tzinfo is None for bound in bounds)
        response = api.get("/events/", params={"date": selector})
        assert response.status_code == 200
        expected = api.get("/events/", params={"date_from": start, "date_to": (bounds[1] - module.timedelta(days=1)).strftime("%Y-%m-%d")})
        assert response.json() == expected.json()
    finally:
        if original_tz is None:
            monkeypatch.delenv("TZ")
        else:
            monkeypatch.setenv("TZ", original_tz)
        time.tzset()


def test_category_pagination_and_descending_order(api):
    params = {"date": "2026-11-12", "category": "business", "limit": 2, "sort": "desc"}
    first = api.get("/events/", params=params).json()
    second = api.get("/events/", params={**params, "page": 2}).json()
    assert [item["title"] for item in first["items"]] == ["micro", "late"]
    assert [item["title"] for item in second["items"]] == ["start"]
    assert first["total_items"] == second["total_items"] == 3
    assert first["total_pages"] == second["total_pages"] == 2
    assert second["page"] == 2
    empty = api.get("/events/", params={"date": "2026-11-12", "category": "missing"}).json()
    assert empty["items"] == [] and empty["total_items"] == 0


def test_unfiltered_admin_list_contract(api):
    response = api.get("/events/", params={"limit": 100})
    assert response.status_code == 200
    assert set(response.json()) == {"items", "page", "limit", "total_items", "total_pages"}
    assert response.json()["total_items"] == 11


def test_real_http_over_loopback(api):
    # Exercise actual HTTP serialization over a private ephemeral TCP socket.
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
            url = f"http://127.0.0.1:{sock.getsockname()[1]}/events/"
            with urlopen(url + "?date=2026-11-12", timeout=5) as response:
                assert response.status == 200
                assert json.load(response)["total_items"] == 4
            with pytest.raises(HTTPError) as error:
                urlopen(url + "?date=2026-02-30&category=missing", timeout=5)
            assert error.value.code == 400
            assert json.load(error.value) == {"detail": "Invalid calendar date"}
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive()
