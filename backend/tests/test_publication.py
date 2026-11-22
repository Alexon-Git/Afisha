"""HTTP editorial workflow using real JWT validation and isolated event storage."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from jose import jwt

from app.auth.auth import create_access_token
from app.config import settings
from app.database import get_db
from app.main import app
from app.models.event import Event
from app.models.organizer import Organizer
from app.models.user import User
from app.services.event_service import EventService


NOW = datetime(2026, 11, 15, 10, tzinfo=timezone.utc)


@pytest.fixture
def editorial(event_sessions, monkeypatch):
    with event_sessions.begin() as db:
        db.add(Organizer(id=1, name="Club", public_contact="Designated public editorial contact"))
        db.add_all([User(id=2, username="reader", password_hash="test-only", is_admin=False),
                    User(id=3, username="no-admin", password_hash="test-only", is_admin=None)])
        db.flush()
        first = db.get(Event, 1)
        first.organizer_id, first.event_url, first.source = 1, "https://example.org/event", "https://example.org/source"
        for identifier, publication, status in [(2, "published", "scheduled"), (3, "archived", "scheduled"),
                                                (4, "published", "cancelled"), (5, "published", "postponed")]:
            db.add(Event(id=identifier, title=f"Event {identifier}", datetime=datetime(2026, 11, 14 + identifier, 12, tzinfo=timezone.utc),
                         location="NSK", category_id=1, organizer_id=1, event_url="https://example.org/event",
                         source="https://example.org/source", verified_at=NOW,
                         publication_status=publication, event_status=status))
        db.add(Event(id=6, title=" ", datetime=datetime(2026, 11, 20, tzinfo=timezone.utc), location=""))
    previous = app.dependency_overrides.copy()

    def session():
        with event_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = session
    clock = [NOW]
    monkeypatch.setattr(EventService, "_utc_now", staticmethod(lambda: clock[0]))
    headers = {"Authorization": "Bearer " + create_access_token({"sub": "test-admin"})}
    try:
        with TestClient(app) as client:
            yield client, headers, clock
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def admin_get(editorial, identifier=1):
    client, headers, _ = editorial
    response = client.get(f"/admin/events/{identifier}", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_public_organizer_summary_discloses_only_name(editorial):
    client, _, _ = editorial
    detail = client.get('/events/2')
    assert detail.status_code == 200
    assert detail.json()['organizer'] == {'name': 'Club'}
    listing = client.get('/events/').json()
    for item in listing['items']:
        assert item['organizer'] == {'name': 'Club'}
    assert 'Designated public editorial contact' not in detail.text
    assert 'public_contact' not in detail.text
    assert client.get('/events/1').status_code == 404
    assert client.get('/events/3').status_code == 404


@pytest.mark.parametrize("params", [{}, {"include_drafts": "true"}, {"include_unpublished": "true"},
                                    {"status": "draft"}, {"publication_status": "draft"}])
def test_public_visibility_cannot_be_overridden(editorial, params):
    client, headers, _ = editorial
    for auth in ({}, headers):
        response = client.get("/events/", params=params, headers=auth)
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [2, 4, 5]
        assert response.json()["total_items"] == 3
        assert all(item["publication_status"] == "published" for item in response.json()["items"])


@pytest.mark.parametrize("identifier", [1, 3, 6, 999])
def test_hidden_and_missing_ids_are_indistinguishable(editorial, identifier):
    client, headers, _ = editorial
    for auth in ({}, headers):
        response = client.get(f"/events/{identifier}", headers=auth)
        assert response.status_code == 404 and response.json() == {"detail": "Event not found"}


def test_public_count_pages_dates_categories_and_admin_catalog(editorial):
    client, headers, _ = editorial
    first = client.get("/events/", params={"limit": 2, "sort": "desc"}).json()
    second = client.get("/events/", params={"limit": 2, "sort": "desc", "page": 2}).json()
    assert [item["id"] for item in first["items"]] == [5, 4]
    assert [item["id"] for item in second["items"]] == [2]
    assert first["total_items"] == second["total_items"] == 3
    assert first["total_pages"] == second["total_pages"] == 2
    response = client.get("/events/", params={"date_from": "2026-11-16", "date_to": "2026-11-18", "category": "business"}).json()
    assert [item["id"] for item in response["items"]] == [2, 4]
    all_items = client.get("/admin/events/", headers=headers, params={"limit": 2, "page": 3}).json()
    assert all_items["total_items"] == 6 and all_items["total_pages"] == 3
    assert len(all_items["items"]) == 2
    assert admin_get(editorial, 1)["publication_status"] == "draft"
    assert admin_get(editorial, 3)["publication_status"] == "archived"
    assert client.get("/admin/events/", headers=headers, params={"date": "bad"}).status_code == 400


@pytest.mark.parametrize("identifier,status", [(2, "scheduled"), (4, "cancelled"), (5, "postponed")])
def test_published_lifecycle_states_remain_public(editorial, identifier, status):
    response = editorial[0].get(f"/events/{identifier}")
    assert response.status_code == 200 and response.json()["event_status"] == status


ENDPOINTS = [("get", "/admin/events/", None), ("get", "/admin/events/1", None),
             ("post", "/admin/events/1/verify", None),
             ("patch", "/admin/events/1/publication", {"publication_status": "draft"}),
             ("patch", "/admin/events/1/status", {"event_status": "cancelled"})]


@pytest.mark.parametrize("method,path,payload", ENDPOINTS + [
    ("post", "/events/", {"title": "New", "datetime": "2026-11-15T12:00:00+07:00", "location": "NSK"}),
    ("put", "/events/1", {"description": "Not authorized"}), ("delete", "/events/1", None),
])
@pytest.mark.parametrize("identity", ["anonymous", "garbage", "expired", "reader", "no-admin", "unknown"])
def test_all_editorial_routes_require_current_database_admin(editorial, method, path, payload, identity):
    client = editorial[0]
    token = {
        "anonymous": None, "garbage": "not-a-valid-jwt",
        "expired": jwt.encode({"sub": "test-admin", "exp": 1}, settings.secret_key, algorithm=settings.algorithm),
        "reader": create_access_token({"sub": "reader", "is_admin": True}),
        "no-admin": create_access_token({"sub": "no-admin", "is_admin": True}),
        "unknown": create_access_token({"sub": "missing"}),
    }[identity]
    kwargs = {"headers": {"Authorization": "Bearer " + token} if token else {}}
    if payload is not None:
        kwargs["json"] = payload
    assert getattr(client, method)(path, **kwargs).status_code in (401, 403)
    assert admin_get(editorial)["verified_at"] is None


def test_incomplete_publication_returns_field_errors_without_commit(editorial):
    client, headers, _ = editorial
    before = admin_get(editorial, 6)
    response = client.patch("/admin/events/6/publication", headers=headers, json={"publication_status": "published"})
    assert response.status_code == 422
    assert set(response.json()["detail"]["fields"]) == {"title", "location", "organizer_id", "event_url", "source", "verified_at"}
    assert admin_get(editorial, 6) == before


def test_verify_is_explicit_server_utc_and_repeatable_then_publish(editorial):
    client, headers, clock = editorial
    assert admin_get(editorial)["verified_at"] is None
    response = client.post("/admin/events/1/verify", headers=headers, json={"verified_at": "1900-01-01T00:00:00Z"})
    assert response.status_code == 200
    assert response.json()["verified_at"] == "2026-11-15T10:00:00Z"
    assert response.json()["publication_status"] == "draft"
    clock[0] += timedelta(minutes=5)
    assert client.post("/admin/events/1/verify", headers=headers).json()["verified_at"] == "2026-11-15T10:05:00Z"
    response = client.patch("/admin/events/1/publication", headers=headers, json={"publication_status": "published"})
    assert response.status_code == 200
    assert client.get("/events/1").json()["publication_status"] == "published"
    assert client.patch("/admin/events/1/publication", headers=headers, json={"publication_status": "archived"}).status_code == 200
    assert client.get("/events/1").status_code == 404


@pytest.mark.parametrize("field,value", [("title", ""), ("location", " "), ("datetime", "2026-12-01T12:00:00+07:00"),
                                       ("organizer_id", None), ("event_url", None), ("source", None)])
def test_published_critical_updates_are_atomic_and_require_draft(editorial, field, value):
    client, headers, _ = editorial
    before = admin_get(editorial, 2)
    response = client.put("/events/2", headers=headers, json={"description": "must not change", field: value})
    assert response.status_code == 422
    assert admin_get(editorial, 2) == before


def test_critical_edit_invalidates_check_and_requires_reverification(editorial):
    client, headers, _ = editorial
    assert client.patch("/admin/events/2/publication", headers=headers, json={"publication_status": "draft"}).status_code == 200
    edited = client.put("/events/2", headers=headers, json={"location": "New place"})
    assert edited.status_code == 200 and edited.json()["verified_at"] is None
    assert client.patch("/admin/events/2/publication", headers=headers, json={"publication_status": "published"}).status_code == 422
    assert client.post("/admin/events/2/verify", headers=headers).status_code == 200
    assert client.patch("/admin/events/2/publication", headers=headers, json={"publication_status": "published"}).status_code == 200
    assert client.get("/events/2").json()["location"] == "New place"


def test_noncritical_edit_preserves_check_but_revalidates_result(editorial, event_sessions):
    client, headers, _ = editorial
    before = admin_get(editorial, 2)
    response = client.put("/events/2", headers=headers, json={"description": "Updated", "title": before["title"]})
    assert response.status_code == 200 and response.json()["verified_at"] == before["verified_at"]
    with event_sessions.begin() as db:
        db.get(Event, 2).source = "javascript:invalid-legacy-source"
    response = client.put("/events/2", headers=headers, json={"description": "must not save"})
    assert response.status_code == 422 and "source" in response.json()["detail"]["fields"]
    assert admin_get(editorial, 2)["description"] == "Updated"


@pytest.mark.parametrize("status", ["cancelled", "postponed"])
def test_event_status_has_protected_draft_verify_publish_workflow(editorial, status):
    client, headers, _ = editorial
    before = admin_get(editorial, 2)
    assert client.patch("/admin/events/2/status", headers=headers, json={"event_status": status}).status_code == 422
    assert admin_get(editorial, 2) == before
    assert client.patch("/admin/events/2/publication", headers=headers, json={"publication_status": "draft"}).status_code == 200
    assert client.patch("/admin/events/2/status", headers=headers, json={"event_status": status}).json()["verified_at"] is None
    assert client.post("/admin/events/2/verify", headers=headers).status_code == 200
    assert client.patch("/admin/events/2/publication", headers=headers, json={"publication_status": "published"}).status_code == 200
    assert client.get("/events/2").json()["event_status"] == status


@pytest.mark.parametrize("field,value", [("publication_status", "published"), ("event_status", "cancelled"), ("verified_at", None)])
def test_ordinary_write_cannot_bypass_workflow(editorial, field, value):
    client, headers, _ = editorial
    assert client.put("/events/1", headers=headers, json={field: value}).status_code == 422
    assert client.post("/events/", headers=headers,
                       json={"title": "Draft", "datetime": "2026-11-15T12:00:00+07:00", "location": "NSK", field: value}).status_code == 422


@pytest.mark.parametrize("method,path,payload", ENDPOINTS[1:])
def test_editorial_missing_event_is_404(editorial, method, path, payload):
    client, headers, _ = editorial
    kwargs = {"headers": headers}
    if payload is not None:
        kwargs["json"] = payload
    assert getattr(client, method)(path.replace("/1", "/999"), **kwargs).status_code == 404


@pytest.mark.parametrize("contact,name", [(None, "Club"), (" ", "Club"), ("Public contact", " ")])
def test_organizer_minimum_information_is_required(editorial, event_sessions, contact, name):
    client, headers, _ = editorial
    with event_sessions.begin() as db:
        organizer = db.get(Organizer, 1)
        organizer.name, organizer.public_contact = name, contact
    assert client.post("/admin/events/1/verify", headers=headers).status_code == 200
    before = admin_get(editorial)
    response = client.patch("/admin/events/1/publication", headers=headers, json={"publication_status": "published"})
    assert response.status_code == 422 and "organizer_id" in response.json()["detail"]["fields"]
    assert admin_get(editorial) == before


@pytest.mark.parametrize("path,payload", [
    ("publication", {"publication_status": "cancelled"}), ("status", {"event_status": "published"}),
    ("publication", {"publication_status": "published", "verified_at": "2026-11-15T10:00:00Z"}),
])
def test_editorial_payload_is_strict(editorial, path, payload):
    client, headers, _ = editorial
    before = admin_get(editorial)
    assert client.patch(f"/admin/events/1/{path}", headers=headers, json=payload).status_code == 422
    assert admin_get(editorial) == before
