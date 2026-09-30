from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import routes
from app.services.demo_generator import generate_demo_outline
from app.services.gemini_flash import GeminiGenerationError
from app.services.image_generator import ImageResult, _create_placeholder


client = TestClient(app)


def _offline_image(prompt, panel_number, art_style="comic book", character_name="hero", output_dir=None):
    path = _create_placeholder(panel_number, output_dir)
    return ImageResult(path=path, url=f"/static/panels/{path.name}", generated=False, error="offline test")


def _payload():
    return {
        "story_prompt": "A curious fox finds a glowing compass that points toward whoever needs help.",
        "character_name": "Pip",
        "setting": "an enchanted forest",
        "tone": "Adventurous",
        "art_style": "Classic comic book",
    }


def _install_offline_pipeline(monkeypatch):
    def unavailable(_payload):
        raise GeminiGenerationError("No test API key configured")

    monkeypatch.setattr(routes, "generate_outline", unavailable)
    monkeypatch.setattr(routes, "generate_image", _offline_image)


def test_homepage_and_route_manifest_are_available():
    response = client.get("/")
    assert response.status_code == 200
    assert "A little idea." in response.text
    assert "Demo mode is ready" in response.text

    manifest = client.get("/manus-routes.json")
    assert manifest.status_code == 200
    assert manifest.json()["routes"][0]["path"] == "/"
    assert client.get("/health").json()["status"] == "ok"


def test_browser_generation_shows_exactly_five_panels(monkeypatch):
    _install_offline_pipeline(monkeypatch)
    response = client.post("/generate", data=_payload())
    assert response.status_code == 200
    assert response.text.count('class="comic-panel"') == 5
    assert "Demo story mode is active" in response.text
    assert "Image generation unavailable" in response.text


def test_json_generation_returns_five_panels_and_pdf_url(monkeypatch):
    _install_offline_pipeline(monkeypatch)
    response = client.post("/generate-comic/json", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert len(body["panels"]) == 5
    assert body["ai_mode"] == "demo"
    assert body["pdf_url"].startswith("/static/exports/")
    assert client.get(body["pdf_url"]).status_code == 200
    export = client.post(f"/export/{body['comic_id']}", follow_redirects=False)
    assert export.status_code == 303
    assert export.headers["location"].startswith("/export-success?file=")
    success = client.get(export.headers["location"])
    assert success.status_code == 200
    assert "Your comic is" in success.text
    assert "Download PDF" in success.text


def test_invalid_form_shows_friendly_validation_message():
    response = client.post("/generate", data={**_payload(), "character_name": ""})
    assert response.status_code == 422
    assert "Please check the form fields" in response.text


def test_test_image_route_uses_placeholder_without_api(monkeypatch):
    monkeypatch.setattr(routes, "generate_image", _offline_image)
    response = client.post("/test-image", data={"prompt": "A moonlit forest", "panel_number": "2"})
    assert response.status_code == 200
    assert response.json()["status"] == "placeholder"
    assert "/static/panels/" in response.json()["image_url"]


def test_preview_route_returns_not_found_for_unknown_comic():
    response = client.get("/preview/does-not-exist")
    assert response.status_code == 404
    assert "no longer in this session" in response.text
