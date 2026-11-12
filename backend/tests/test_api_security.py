"""Minimal API smoke tests; must not require a live database."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_route():
    result = client.get("/health")
    assert result.status_code == 200
    assert result.json()["status"] == "healthy"

def test_public_user_registration_requires_admin():
    response = client.post("/auth/register", json={
        "username": "newuser",
        "email": "newuser@example.org",
        "password": "StrongTestPassword123",
    })
    assert response.status_code in (401, 403)

def test_public_event_creation_requires_admin():
    response = client.post("/events/", json={
        "title": "Do not create", "datetime": "2027-01-02T11:00:00",
        "location": "Nowhere",
    })
    assert response.status_code in (401, 403)
