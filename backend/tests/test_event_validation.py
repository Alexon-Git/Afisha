"""Write API rejects invalid data before changing the event."""

import pytest
from sqlalchemy import func, select

from app.models.event import Event
from app.schemas.event import EventUpdate
from app.services.event_service import EventService
from app.services.exceptions import CategoryNotFoundError


CREATE = {"title": "New", "datetime": "2026-11-15T12:00:00", "location": "Novosibirsk"}


@pytest.mark.parametrize("field", ["title", "datetime", "location"])
def test_explicit_null_required_field_is_422(event_api, field):
    before = event_api.get("/events/1").json()
    response = event_api.put("/events/1", json={"description": "must not save", field: None})
    assert response.status_code == 422
    assert event_api.get("/events/1").json() == before


def test_partial_update_keeps_omitted_fields(event_api):
    before = event_api.get("/events/1").json()
    response = event_api.put("/events/1", json={"description": "Changed"})
    assert response.status_code == 200
    assert response.json() == {**before, "description": "Changed"}
    assert event_api.put("/events/1", json={}).json() == response.json()


@pytest.mark.parametrize("method", ["post", "put"])
def test_missing_category_returns_422_without_partial_write(event_api, event_sessions, method):
    before = event_api.get("/events/1").json()
    response = getattr(event_api, method)("/events/" if method == "post" else "/events/1",
                                         json={**CREATE, "category_id": 999})
    assert response.status_code == 422
    assert response.json() == {"detail": "Category not found"}
    assert event_api.get("/events/1").json() == before
    with event_sessions() as db:
        assert db.scalar(select(func.count()).select_from(Event)) == 1
        with pytest.raises(CategoryNotFoundError):
            EventService(db).update_event(1, EventUpdate(title="not applied", category_id=999))
        assert not db.dirty


@pytest.mark.parametrize("method", ["post", "put"])
@pytest.mark.parametrize("category_id", [None, 1])
def test_valid_and_null_category(event_api, method, category_id):
    response = getattr(event_api, method)("/events/" if method == "post" else "/events/1",
                                         json={**CREATE, "category_id": category_id})
    assert response.status_code == 200
    assert response.json()["category_id"] == category_id
    assert (response.json()["category"] is None) == (category_id is None)


@pytest.mark.parametrize("method", ["post", "put"])
@pytest.mark.parametrize("field,value", [
    ("price", -1), ("rating", -0.1), ("rating", 10.1), ("discount", -1), ("discount", 101),
])
def test_numeric_limits_reject_invalid_values(event_api, method, field, value):
    before = event_api.get("/events/1").json()
    response = getattr(event_api, method)("/events/" if method == "post" else "/events/1",
                                         json={**CREATE, field: value})
    assert response.status_code == 422
    assert event_api.get("/events/1").json() == before


@pytest.mark.parametrize("numbers", [
    {"price": 0, "rating": 0, "discount": 0},
    {"price": 1500, "rating": 10, "discount": 100},
    {"price": None, "rating": None, "discount": None},
])
def test_valid_numeric_boundaries(event_api, numbers):
    response = event_api.post("/events/", json={**CREATE, **numbers})
    assert response.status_code == 200
    assert {key: response.json()[key] for key in numbers} == numbers


def test_unknown_event_still_returns_404(event_api):
    assert event_api.put("/events/999", json={"title": "New"}).status_code == 404
