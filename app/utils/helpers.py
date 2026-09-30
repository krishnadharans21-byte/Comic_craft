"""Small filesystem and parsing helpers shared by ComicCraft services."""
from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4


def ensure_project_dirs(*directories: Path) -> None:
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def safe_filename(prefix: str, suffix: str = ".png") -> str:
    """Return a short, filesystem-safe, collision-resistant filename."""
    clean_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", prefix).strip("_-") or "file"
    clean_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    clean_suffix = re.sub(r"[^.a-zA-Z0-9]+", "", clean_suffix)[:12] or ".bin"
    return f"{clean_prefix}_{uuid4().hex[:12]}{clean_suffix}"


def extract_json_object(text: str) -> str:
    """Remove optional Markdown fences and return the first complete JSON object."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("The model response did not contain a JSON object.")
    try:
        _, end = json.JSONDecoder().raw_decode(cleaned[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"The model returned malformed JSON: {exc.msg}") from exc
    return cleaned[start : start + end]


def truncate_text(value: str, limit: int = 180) -> str:
    value = " ".join((value or "").split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"
