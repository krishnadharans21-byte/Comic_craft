"""Application settings and filesystem paths."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    huggingface_api_key: str
    gemini_outline_model: str
    gemini_story_model: str
    image_provider: str
    image_model: str
    image_timeout: int
    pdf_font_path: str
    app_env: str
    log_level: str
    demo_mode: str

    @classmethod
    def from_environment(cls) -> "Settings":
        try:
            timeout = max(15, min(600, int(os.getenv("IMAGE_TIMEOUT", "120"))))
        except ValueError:
            timeout = 120
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY", "").strip(),
            gemini_outline_model=os.getenv(
                "GEMINI_OUTLINE_MODEL",
                os.getenv("GEMINI_TEXT_MODEL", "gemini-3.8-flash"),
            ).strip(),
            gemini_story_model=os.getenv("GEMINI_STORY_MODEL", "gemini-3.1-pro-preview").strip(),
            image_provider=os.getenv("IMAGE_PROVIDER", "huggingface").strip().lower(),
            image_model=os.getenv(
                "IMAGE_MODEL", "stabilityai/stable-diffusion-3-medium-diffusers"
            ).strip(),
            image_timeout=timeout,
            pdf_font_path=os.getenv("PDF_FONT_PATH", "").strip(),
            app_env=os.getenv("APP_ENV", "development").strip().lower(),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            demo_mode=os.getenv("DEMO_MODE", "auto").strip().lower(),
        )

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def image_configured(self) -> bool:
        return self.image_provider == "huggingface" and bool(self.huggingface_api_key)


settings = Settings.from_environment()
STATIC_DIR = PROJECT_ROOT / "static"
PANELS_DIR = STATIC_DIR / "panels"
EXPORTS_DIR = STATIC_DIR / "exports"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
