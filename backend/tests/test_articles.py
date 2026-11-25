"""Blog API: editorial workflow, public visibility, validation, auth."""
import pytest
from fastapi.testclient import TestClient

from app.auth.auth import get_current_admin_user
from app.main import app
from app.services.article_service import slugify

BODY = "Содержательный текст статьи для предпринимателей. " * 8


def make(client, **over):
    data = {"title": "Как выбрать деловое мероприятие", "excerpt": "Кратко", "content": BODY,
            "seo_description": "Описание для поиска", "category": "guides"}
    data.update(over)
    return client.post("/admin/articles/", json=data)


def test_create_draft_generates_slug_and_server_fields(event_api):
    r = make(event_api)
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "kak-vybrat-delovoe-meropriyatie"
    assert body["publication_status"] == "draft" and body["published_at"] is None


def test_client_cannot_set_controlled_fields(event_api):
    for field, value in [("publication_status", "published"), ("published_at", "2026-01-01T00:00:00Z"), ("id", 5)]:
        assert make(event_api, **{field: value}).status_code == 422


def test_empty_draft_and_invalid_input(event_api):
    assert event_api.post("/admin/articles/", json={"title": "Черновик", "slug": "draft-one"}).status_code == 201
    assert event_api.post("/admin/articles/", json={"title": "  "}).status_code == 422
    assert make(event_api, slug="Bad Slug").status_code == 422
    assert make(event_api, slug="x" * 121).status_code == 422
    assert make(event_api, cover_image_url="javascript:alert(1)").status_code == 422
    assert make(event_api, title="x" * 201).status_code == 422


def test_slug_unique(event_api):
    assert make(event_api, slug="same").status_code == 201
    assert make(event_api, slug="same").status_code == 409


def test_partial_edit_and_published_slug_locked(event_api):
    aid = make(event_api, slug="one").json()["id"]
    r = event_api.put(f"/admin/articles/{aid}", json={"excerpt": "Новое"})
    assert r.status_code == 200 and r.json()["excerpt"] == "Новое" and r.json()["title"].startswith("Как")
    assert event_api.put(f"/admin/articles/{aid}", json={"title": None}).status_code == 422
    assert event_api.post(f"/admin/articles/{aid}/publish").status_code == 200
    assert event_api.put(f"/admin/articles/{aid}", json={"slug": "two"}).status_code == 409
    assert event_api.put(f"/admin/articles/{aid}", json={"slug": "one", "excerpt": "ok"}).status_code == 200
    assert event_api.put(f"/admin/articles/{aid}", json={"content": "коротко"}).status_code == 422


def test_publish_requires_complete_article(event_api):
    aid = event_api.post("/admin/articles/", json={"title": "Пусто"}).json()["id"]
    r = event_api.post(f"/admin/articles/{aid}/publish")
    assert r.status_code == 422
    assert {"content", "excerpt", "seo_description"} <= set(r.json()["detail"]["fields"])
    assert event_api.get("/articles/").json()["total_items"] == 0


def test_public_visibility_lifecycle(event_api):
    aid = make(event_api, slug="life").json()["id"]
    assert event_api.get("/articles/life").status_code == 404
    first = event_api.post(f"/admin/articles/{aid}/publish").json()
    assert first["publication_status"] == "published" and first["published_at"]
    page = event_api.get("/articles/").json()
    assert [i["slug"] for i in page["items"]] == ["life"]
    assert "publication_status" not in page["items"][0] and "id" not in page["items"][0]
    assert event_api.get("/articles/life?include_unpublished=true").status_code == 200
    event_api.post(f"/admin/articles/{aid}/unpublish")
    assert event_api.get("/articles/life").status_code == 404
    assert event_api.get("/articles/").json()["total_items"] == 0
    again = event_api.post(f"/admin/articles/{aid}/publish").json()
    assert again["published_at"] == first["published_at"]
    event_api.post(f"/admin/articles/{aid}/archive")
    assert event_api.get("/articles/life").status_code == 404
    assert event_api.get("/articles/", params={"status": "archived"}).json()["total_items"] == 0


def test_pagination_sort_category(event_api):
    for n in range(5):
        aid = make(event_api, slug=f"a{n}", category="guides" if n % 2 == 0 else "news").json()["id"]
        event_api.post(f"/admin/articles/{aid}/publish")
    r = event_api.get("/articles/", params={"limit": 2, "page": 2}).json()
    assert r["total_items"] == 5 and r["total_pages"] == 3 and len(r["items"]) == 2
    assert [i["slug"] for i in event_api.get("/articles/", params={"sort": "asc"}).json()["items"]][0] == "a0"
    assert event_api.get("/articles/", params={"category": "news"}).json()["total_items"] == 2
    assert event_api.get("/articles/categories").json() == ["guides", "news"]
    assert event_api.get("/articles/", params={"page": 0}).status_code == 422
    assert event_api.get("/articles/", params={"sort": "x"}).status_code == 422


def test_admin_endpoints_require_auth(event_api):
    app.dependency_overrides.pop(get_current_admin_user)
    paths = [("get", "/admin/articles/"), ("get", "/admin/articles/1"), ("post", "/admin/articles/"),
             ("put", "/admin/articles/1"), ("post", "/admin/articles/1/publish"),
             ("post", "/admin/articles/1/unpublish"), ("post", "/admin/articles/1/archive"),
             ("post", "/admin/articles/upload-cover")]
    for method, path in paths:
        assert getattr(event_api, method)(path).status_code in (401, 403), path


def test_events_api_unaffected(event_api):
    assert event_api.get("/events/").status_code == 200
    assert event_api.get("/admin/articles/999").status_code == 404


def test_slugify_russian():
    assert slugify("Деловой завтрак: 5 советов!") == "delovoi-zavtrak-5-sovetov"
    assert slugify("!!!") == ""
