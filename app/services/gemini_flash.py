"""Gemini Flash service for validated, exactly-five-panel comic outlines."""
from __future__ import annotations

import logging

from google import genai
from google.genai import types

from app.config import settings
from app.models import ComicOutline, ComicRequest
from app.utils.helpers import extract_json_object

logger = logging.getLogger(__name__)


class GeminiGenerationError(RuntimeError):
    """Raised when Gemini is not configured or its response cannot be validated."""


def generate_outline(request: ComicRequest) -> ComicOutline:
    if not settings.gemini_api_key:
        raise GeminiGenerationError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"""Create a connected comic outline using exactly five panels and the supplied schema.
The panels must follow this exact arc: panel 1 introduction/setup, panel 2 problem/conflict,
panel 3 development/escalation, panel 4 climax, panel 5 resolution/conclusion.
Make the image prompts detailed and useful for landscape comic-style illustrations. Define the
main character's stable visual appearance in panel 1 and repeat the same appearance details in
every image prompt. Do not include visible written words, captions, or speech bubbles in images.

Story idea: {request.story_prompt}
Main character: {request.character_name}
Setting: {request.setting}
Tone: {request.tone}
Art style: {request.art_style}

Return one JSON object with a `panels` array. Each item needs panel_number, title,
scene_description, and image_prompt. No extra panels or prose outside the JSON."""
    repair_note = ""
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=settings.gemini_outline_model,
                contents=prompt + repair_note,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ComicOutline,
                    temperature=1.0,
                    max_output_tokens=5000,
                ),
            )
            raw_text = getattr(response, "text", None) or ""
            parsed = ComicOutline.model_validate_json(extract_json_object(raw_text))
            return parsed
        except Exception as exc:
            logger.warning("Gemini outline attempt %s failed: %s", attempt + 1, exc)
            if attempt == 0 and isinstance(exc, (ValueError,)):
                repair_note = "\nThe previous response was malformed. Return valid JSON only, with exactly five ordered panels and all required fields."
                continue
            raise GeminiGenerationError(f"Gemini outline generation failed: {exc}") from exc
    raise GeminiGenerationError("Gemini did not return a valid five-panel outline.")
