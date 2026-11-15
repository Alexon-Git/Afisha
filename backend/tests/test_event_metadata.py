"""PR-6: additive metadata, protected editorial fields and private contacts."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.models.event import Event
from app.models.event_status import EventStatus, PublicationStatus
from app.models.organizer import Organizer


OLD_REQUEST = {"title": "New event", "datetime": "2026-11-15T12:30:00", "location": "Novosibirsk"}


def test_organizer_fields_relationship_and_safe_deletion(event_sessions):
    with event_sessions.begin() as db:
        organizer = Organizer(name="Business club", description="Editorial description",
                              website_url="https://example.org/", public_contact="test-public@example.org")
        db.add(organizer)
        db.flush()
        identifier = organizer.id
        assert organizer.created_at is not None and organizer.updated_at is not None
        db.get(Event, 1).organizer = organizer
        db.add(Event(title="Second", datetime=datetime(2026, 11, 16), location="NSK", organizer=organizer))
    with event_sessions.begin() as db:
        organizer = db.get(Organizer, identifier)
        assert len(organizer.events) == 2
        assert organizer.description == "Editorial description"
        assert organizer.website_url == "https://example.org/"
        assert organizer.public_contact == "test-public@example.org"
        organizer.description = "Updated"
    with event_sessions.begin() as db:
        assert db.get(Organizer, identifier).updated_at is not None
        # Raw deletion exercises the FK rather than ORM relationship handling.
        db.execute(text("DELETE FROM organizers WHERE id=:id"), {"id": identifier})
    with event_sessions() as db:
        events = list(db.scalars(select(Event)))
        assert len(events) == 2 and all(item.organizer_id is None for item in events)


def test_minimal_organizer_and_required_name(event_sessions):
    with event_sessions.begin() as db:
        organizer = Organizer(name="Minimal")
        db.add(organizer)
        db.flush()
        assert organizer.description is organizer.website_url is organizer.public_contact is None
    with event_sessions() as db, pytest.raises(IntegrityError):
        db.add(Organizer(name=None))
        db.flush()


def test_legacy_http_contract_and_new_defaults(event_api):
    created = event_api.post("/events/", json={**OLD_REQUEST, "payment_url": "https://payments.example.org/legacy"})
    assert created.status_code == 200
    body = created.json()
    assert all(body[key] == value for key, value in OLD_REQUEST.items())
    assert body["payment_url"] == "https://payments.example.org/legacy"
    assert body["organizer_id"] is body["event_url"] is body["source"] is body["verified_at"] is None
    assert body["publication_status"] == "draft" and body["event_status"] == "scheduled"
    identifier = body["id"]
    assert event_api.get(f"/admin/events/{identifier}").json() == body
    assert event_api.put(f"/events/{identifier}", json={"title": "Edited"}).status_code == 200
    assert event_api.get(f"/events/{identifier}").status_code == 404
    assert identifier not in {item["id"] for item in event_api.get("/events/").json()["items"]}
    # Administrative access preserves the legacy editor's reading contract.
    assert identifier in {item["id"] for item in event_api.get("/admin/events/").json()["items"]}


@pytest.mark.parametrize("method", ["post", "put"])
def test_assign_clear_organizer_without_exposing_contact(event_api, event_sessions, method):
    with event_sessions.begin() as db:
        db.add(Organizer(id=1, name="Club", public_contact="must-not-be-in-public-response"))
    url = "/events/" if method == "post" else "/events/1"
    response = getattr(event_api, method)(url, json={**OLD_REQUEST, "organizer_id": 1})
    assert response.status_code == 200
    assert response.json()["organizer_id"] == 1
    assert "must-not-be-in-public-response" not in response.text
    assert "public_contact" not in response.text
    identifier = response.json()["id"]
    assert "public_contact" not in event_api.get(f"/admin/events/{identifier}").text
    assert "public_contact" not in event_api.get("/admin/events/").text
    assert event_api.put(f"/events/{identifier}", json={"organizer_id": None}).json()["organizer_id"] is None


@pytest.mark.parametrize("method", ["post", "put"])
@pytest.mark.parametrize("identifier", [999, 0, -1, 2147483648])
def test_invalid_organizer_is_422_and_does_not_partially_edit(event_api, method, identifier):
    before = event_api.get("/admin/events/1").json()
    url = "/events/" if method == "post" else "/events/1"
    response = getattr(event_api, method)(url, json={**OLD_REQUEST, "organizer_id": identifier})
    assert response.status_code == 422
    assert event_api.get("/admin/events/1").json() == before
    assert event_api.get("/admin/events/").json()["total_items"] == 1


@pytest.mark.parametrize("field", ["event_url", "source"])
@pytest.mark.parametrize("url", ["https://example.org/events/1?q=2#part", "http://example.org/register", None])
def test_http_links_can_be_set_and_cleared(event_api, field, url):
    response = event_api.post("/events/", json={**OLD_REQUEST, field: url})
    assert response.status_code == 200 and response.json()[field] == url
    identifier = response.json()["id"]
    assert event_api.put(f"/events/{identifier}", json={field: None}).json()[field] is None


@pytest.mark.parametrize("field", ["event_url", "source"])
@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "data:text/plain,test", "file:///tmp/a", "ftp://example.org/a",
    "//example.org/a", "/relative", "https://", "https://user:password@example.org/a",
    "https://example.org/\npath", "https://example.org\\evil", " https://example.org/",
    "http:example.org", "https:///example.org",
])
def test_invalid_links_rejected_before_write(event_api, field, url):
    before = event_api.get("/admin/events/1").json()
    for method, path in [("post", "/events/"), ("put", "/events/1")]:
        response = getattr(event_api, method)(path, json={**OLD_REQUEST, field: url})
        assert response.status_code == 422
    assert event_api.get("/admin/events/1").json() == before
    assert event_api.get("/admin/events/").json()["total_items"] == 1


@pytest.mark.parametrize("field,value", [
    ("publication_status", "published"), ("publication_status", "draft"), ("publication_status", "invalid"),
    ("event_status", "cancelled"), ("event_status", "invalid"),
    ("verified_at", "2026-11-15T00:00:00Z"), ("verified_at", None),
])
def test_general_api_cannot_write_controlled_fields(event_api, field, value):
    before = event_api.get("/admin/events/1").json()
    for method, path in [("post", "/events/"), ("put", "/events/1")]:
        assert getattr(event_api, method)(path, json={**OLD_REQUEST, field: value}).status_code == 422
    assert event_api.get("/admin/events/1").json() == before


def test_ordinary_edit_does_not_set_or_update_verification(event_api, event_sessions):
    assert event_api.put("/events/1", json={"title": "Edited"}).json()["verified_at"] is None
    with event_sessions.begin() as db:
        db.get(Event, 1).verified_at = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    before = event_api.get("/admin/events/1").json()["verified_at"]
    assert event_api.put("/events/1", json={"description": "Updated"}).json()["verified_at"] == before


@pytest.mark.parametrize("publication", list(PublicationStatus))
@pytest.mark.parametrize("event_status", list(EventStatus))
def test_statuses_are_independent_in_model_and_database(event_sessions, publication, event_status):
    with event_sessions.begin() as db:
        item = db.get(Event, 1)
        item.publication_status = publication
        item.event_status = event_status
    with event_sessions() as db:
        assert db.get(Event, 1).publication_status == publication
        assert db.get(Event, 1).event_status == event_status


@pytest.mark.parametrize("column", ["publication_status", "event_status"])
def test_invalid_model_status_and_direct_sql_are_rejected(event_sessions, column):
    with event_sessions() as db, pytest.raises(StatementError):
        setattr(db.get(Event, 1), column, "invalid")
        db.flush()
    with event_sessions() as db, pytest.raises(IntegrityError):
        db.execute(text(f"UPDATE events SET {column} = 'invalid' WHERE id = 1"))


def test_metadata_and_legacy_requests_over_real_http(live_event_api, event_sessions):
    with event_sessions.begin() as db:
        db.add(Organizer(id=1, name="Club", public_contact="not-automatically-public"))
    created = live_event_api.post("/events/", json=OLD_REQUEST)
    assert created.status_code == 200
    identifier = created.json()["id"]
    assert created.json()["verified_at"] is None
    assert created.json()["publication_status"] == "draft"
    response = live_event_api.put(f"/events/{identifier}", json={
        "organizer_id": 1, "event_url": "https://example.org/event", "source": "http://example.org/source",
    })
    assert response.status_code == 200
    assert response.json()["organizer_id"] == 1 and response.json()["verified_at"] is None
    assert "public_contact" not in response.text
    for payload in ({"publication_status": "published"}, {"verified_at": None},
                    {"organizer_id": 999}, {"source": "javascript:alert(1)"}):
        assert live_event_api.put(f"/events/{identifier}", json=payload).status_code == 422
    assert live_event_api.get(f"/admin/events/{identifier}").json() == response.json()
