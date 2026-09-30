"""Gemini Pro service for expanding a validated outline into comic-ready story text."""
from __future__ import annotations

import logging

from google import genai
from google.genai import types

from app.config import settings
from app.models import ComicOutline, ComicRequest, ComicStory
from app.utils.helpers import extract_json_object

logger = logging.getLogger(__name__)


class GeminiStoryError(RuntimeError):
    """Raised when detailed Gemini story generation is unavailable."""


def generate_story(
    outline: ComicOutline, character_name: str, setting: str, tone: str, art_style: str
) -> ComicStory:
    if not settings.gemini_api_key:
        raise GeminiStoryError("GEMINI_API_KEY is not configured.")
    request = ComicRequest(
        story_prompt="Expand the supplied outline without changing its story arc.",
        character_name=character_name,
        setting=setting,
        tone=tone,
        art_style=art_style,
    )
    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"""Expand this comic outline into exactly five concise, connected panels.
Preserve the plot, panel order, scene, title, and visual continuity. Use the chosen tone.
Each panel needs panel_number, title, scene_description, caption, narration, and dialogue.
Write one brief caption and 1–3 short dialogue lines per panel; keep each spoken line below
about 16 words and narration below 55 words. Do not add panels or change the ending.
Main character: {request.character_name}
Setting: {request.setting}
Tone: {request.tone}
Art style: {request.art_style}
Outline JSON:
{outline.model_dump_json(indent=2)}
Return valid JSON only, matching the supplied schema."""
    repair_note = ""
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=settings.gemini_story_model,
                contents=prompt + repair_note,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ComicStory,
                    temperature=1.0,
                    max_output_tokens=6000,
                ),
            )
            raw_text = getattr(response, "text", None) or ""
            return ComicStory.model_validate_json(extract_json_object(raw_text))
        except Exception as exc:
            logger.warning("Gemini story attempt %s failed: %s", attempt + 1, exc)
            if attempt == 0 and isinstance(exc, ValueError):
                repair_note = "\nCorrect the previous response. Return valid JSON with exactly five ordered story panels and concise dialogue."
                continue
            raise GeminiStoryError(f"Gemini story generation failed: {exc}") from exc
    raise GeminiStoryError("Gemini did not return a valid five-panel story.")
