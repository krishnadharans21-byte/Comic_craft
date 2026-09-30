from __future__ import annotations

import re
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError

from app.models import ComicDocument, ComicOutline, ComicPanel, ComicRequest, DialogueLine
from app.services import exporters, gemini_flash, gemini_pro, image_generator
from app.services.demo_generator import generate_demo_outline, generate_demo_story
from app.services.exporters import save_pdf
from app.utils.helpers import extract_json_object, safe_filename


def _request() -> ComicRequest:
    return ComicRequest(
        story_prompt="A fox finds a magic map and helps a lost owl.",
        character_name="Pip",
        setting="an enchanted forest",
        tone="Adventurous",
        art_style="Classic comic book",
    )


def test_outline_requires_five_ordered_panels():
    panels = [
        {
            "panel_number": number,
            "title": f"Panel {number}",
            "scene_description": "A connected scene.",
            "image_prompt": "Landscape comic scene, no text.",
        }
        for number in range(1, 6)
    ]
    assert len(ComicOutline(panels=panels).panels) == 5
    with pytest.raises(ValidationError):
        ComicOutline(panels=panels[:4])
    panels[0]["panel_number"] = 2
    with pytest.raises(ValidationError):
        ComicOutline(panels=panels)


def test_json_code_fence_is_removed_safely():
    raw = '```json\n{"panels": [], "ok": true}\n```'
    assert extract_json_object(raw) == '{"panels": [], "ok": true}'
    with pytest.raises(ValueError):
        extract_json_object("not json")
    with pytest.raises(ValueError):
        extract_json_object('{"broken":')


def test_generated_filename_does_not_include_user_prompt():
    filename = safe_filename("panel_3", ".png")
    assert re.fullmatch(r"panel_3_[a-f0-9]{12}\.png", filename)
    assert "fox" not in safe_filename("panel_3", ".png")


def test_gemini_outline_retries_malformed_json_and_validates_response(monkeypatch):
    valid = generate_demo_outline(_request()).model_dump_json()

    class FakeModels:
        def __init__(self):
            self.responses = ["not valid JSON", f"```json\n{valid}\n```"]
            self.calls = []

        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(text=self.responses.pop(0))

    models = FakeModels()
    monkeypatch.setattr(
        gemini_flash,
        "settings",
        SimpleNamespace(gemini_api_key="test-key", gemini_outline_model="gemini-test"),
    )
    monkeypatch.setattr(gemini_flash.genai, "Client", lambda **_kwargs: SimpleNamespace(models=models))

    outline = gemini_flash.generate_outline(_request())
    assert len(outline.panels) == 5
    assert len(models.calls) == 2
    assert models.calls[0]["config"].response_mime_type == "application/json"


def test_gemini_story_returns_structured_narration_and_dialogue(monkeypatch):
    request = _request()
    outline = generate_demo_outline(request)
    story = generate_demo_story(outline, request)

    class FakeModels:
        def generate_content(self, **kwargs):
            assert kwargs["model"] == "gemini-test-pro"
            assert kwargs["config"].response_mime_type == "application/json"
            return SimpleNamespace(text=f"```json\n{story.model_dump_json()}\n```")

    monkeypatch.setattr(
        gemini_pro,
        "settings",
        SimpleNamespace(gemini_api_key="test-key", gemini_story_model="gemini-test-pro"),
    )
    monkeypatch.setattr(gemini_pro.genai, "Client", lambda **_kwargs: SimpleNamespace(models=FakeModels()))

    result = gemini_pro.generate_story(
        outline,
        character_name=request.character_name,
        setting=request.setting,
        tone=request.tone,
        art_style=request.art_style,
    )
    assert len(result.panels) == 5
    assert result.panels[0].narration
    assert result.panels[0].dialogue[0].text


def test_huggingface_provider_failure_logs_falls_back_to_pillow(tmp_path, monkeypatch):
    class BrokenClient:
        def __init__(self, **_kwargs):
            pass

        def text_to_image(self, *args, **kwargs):
            raise RuntimeError("simulated provider outage")

    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "InferenceClient", BrokenClient)
    monkeypatch.setattr(
        image_generator,
        "settings",
        SimpleNamespace(
            image_configured=True,
            image_model="example/model",
            huggingface_api_key="test-token",
            image_timeout=15,
        ),
    )
    result = image_generator.generate_image(
        "A clear landscape comic panel", panel_number=4, output_dir=tmp_path
    )
    assert result.generated is False
    assert "simulated provider outage" in result.error
    assert result.path.is_file()
    with Image.open(result.path) as image:
        assert image.size == (1200, 675)


def test_pdf_export_creates_a_complete_five_page_document(tmp_path, monkeypatch):
    panels_dir = tmp_path / "panels"
    export_dir = tmp_path / "exports"
    panels_dir.mkdir()
    monkeypatch.setattr(exporters, "PANELS_DIR", panels_dir)

    panels = []
    for number in range(1, 6):
        image_name = f"panel_{number}.png"
        Image.new("RGB", (640, 360), "#dce8d5").save(panels_dir / image_name)
        panels.append(
            ComicPanel(
                panel_number=number,
                title=f"Panel {number}",
                scene_description="A connected landscape comic scene.",
                caption="The adventure continues.",
                narration="Pip takes the next brave step.",
                dialogue=[DialogueLine(character="Pip", text="Let's go!")],
                image_url=f"/static/panels/{image_name}",
                image_generated=False,
            )
        )
    comic = ComicDocument(
        title="Pip's Adventurous Comic",
        request=_request(),
        panels=panels,
        ai_mode="demo",
    )
    pdf_path = save_pdf(comic, export_dir=export_dir)
    assert pdf_path.is_file()
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert pdf_path.stat().st_size > 5000
