"""Regression for python-multipart upgrades: form parsing and malformed bodies.

Starlette 0.27 still imports the legacy ``multipart`` alias, which python-multipart
keeps as a deprecated shim for ``python_multipart``. These tests fail if a future
upgrade removes the shim or changes how bodies are parsed.
"""

from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.auth.auth import get_current_admin_user
from app.dependencies import get_event_service
from app.main import app
from app.services.event_service import EventService

BOUNDARY = "testboundary"
MULTIPART = {"content-type": f"multipart/form-data; boundary={BOUNDARY}"}


def png():
    out = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(out, format="PNG")
    return out.getvalue()


def test_starlette_resolves_the_same_parser_as_python_multipart():
    import python_multipart
    import starlette.formparsers as formparsers

    assert formparsers.multipart.MultipartParser is python_multipart.MultipartParser
    assert formparsers.multipart.QuerystringParser is python_multipart.QuerystringParser


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(EventService, "_UPLOAD_DIR", tmp_path / "uploads")
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_event_service] = lambda: EventService(None)
    app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(id=1, is_admin=True)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, tmp_path / "uploads"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def stored(directory):
    return list(directory.iterdir()) if directory.exists() else []


def test_valid_multipart_upload_is_accepted(api):
    client, uploads = api
    response = client.post("/events/upload-image", files={"file": ("a.png", png(), "image/png")})
    assert response.status_code == 200
    assert len(stored(uploads)) == 1


@pytest.mark.parametrize("headers,body", [
    ({"content-type": "multipart/form-data"}, b"--x\r\n"),  # no boundary
    (MULTIPART, b""),  # empty body
    (MULTIPART, b"garbage without any boundary"),
    (MULTIPART, f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.png\"\r\n\r\n".encode()),  # truncated
    (MULTIPART, f"--{BOUNDARY}\r\nbroken header line\r\n\r\ndata\r\n--{BOUNDARY}--\r\n".encode()),
])
def test_malformed_multipart_upload_is_rejected_without_storing(api, headers, body):
    client, uploads = api
    response = client.post("/events/upload-image", headers=headers, content=body)
    assert 400 <= response.status_code < 500
    assert stored(uploads) == []


def test_upload_with_wrong_field_name_is_rejected(api):
    client, uploads = api
    response = client.post("/events/upload-image", files={"other": ("a.png", png(), "image/png")})
    assert response.status_code == 422
    assert stored(uploads) == []


@pytest.mark.parametrize("body,content_type", [
    (b"username=a&password=b", "application/x-www-form-urlencoded"),
    (b"username=a", "application/x-www-form-urlencoded"),
    (b"", "application/x-www-form-urlencoded"),
    (b"username=a&password=b", "multipart/form-data"),  # no boundary
    (b"\xff\xfe=\x00&", "application/x-www-form-urlencoded"),
])
def test_login_form_parsing_never_produces_a_token_or_server_error(body, content_type):
    # Rejected before authentication runs; no database is needed for these inputs.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/auth/login", content=body, headers={"content-type": content_type})
    assert response.status_code in (400, 401, 422, 429, 503)
    assert "access_token" not in response.text
