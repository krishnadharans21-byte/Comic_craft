"""Hugging Face image generation with a reliable local Pillow fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import PANELS_DIR, settings
from app.utils.helpers import ensure_project_dirs, safe_filename

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageResult:
    path: Path
    url: str
    generated: bool
    error: str = ""


def _fallback_font(size: int = 28) -> ImageFont.ImageFont:
    for font_path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _create_placeholder(panel_number: int, output_dir: Path) -> Path:
    ensure_project_dirs(output_dir)
    path = output_dir / safe_filename(f"panel_{panel_number}")
    image = Image.new("RGB", (1200, 675), "#FBF7EE")
    draw = ImageDraw.Draw(image)
    ink, blue, coral, pale = "#1E2024", "#3559E8", "#F16D52", "#F5DF8C"
    draw.rectangle((14, 14, 1185, 660), outline=ink, width=12)
    draw.rectangle((36, 36, 1164, 86), fill=blue)
    draw.text((58, 44), f"COMICCRAFT  /  PANEL {panel_number}", font=_fallback_font(26), fill="white")
    draw.ellipse((480, 140, 710, 370), fill=pale, outline=ink, width=8)
    draw.polygon([(170, 486), (365, 330), (545, 486)], fill="#DCE8D5", outline=ink)
    draw.polygon([(620, 486), (855, 290), (1080, 486)], fill=blue, outline=ink)
    draw.rectangle((100, 500, 1100, 606), fill="white", outline=ink, width=4)
    draw.text((130, 515), "Image generation unavailable", font=_fallback_font(36), fill=ink)
    draw.text((130, 562), f"Panel {panel_number}  ·  Add a Hugging Face token to enable AI art", font=_fallback_font(21), fill=coral)
    image.save(path, format="PNG", optimize=True)
    return path


def _save_generated_image(image: Image.Image, output_dir: Path, panel_number: int) -> Path:
    ensure_project_dirs(output_dir)
    path = output_dir / safe_filename(f"panel_{panel_number}")
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    # Standardize returned provider images into a landscape panel without distorting content.
    image.thumbnail((1200, 675), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1200, 675), "#FBF7EE")
    if image.mode == "RGBA":
        canvas.paste(image, ((1200 - image.width) // 2, (675 - image.height) // 2), image)
    else:
        canvas.paste(image, ((1200 - image.width) // 2, (675 - image.height) // 2))
    canvas.save(path, format="PNG", optimize=True)
    return path


def generate_image(
    image_prompt: str,
    panel_number: int,
    art_style: str = "comic book",
    character_name: str = "the main character",
    output_dir: Path | None = None,
) -> ImageResult:
    """Generate one landscape illustration, or return a visible fallback image."""
    output_dir = output_dir or PANELS_DIR
    prompt = (
        f"{image_prompt.strip()}. {art_style} comic panel, consistent main character "
        f"{character_name}, clear composition, storytelling scene, landscape orientation. "
        "No text, no speech bubbles, no lettering, no captions, no watermark."
    )
    negative_prompt = "text, words, lettering, speech bubbles, watermark, logo, blurry, cropped face"
    if settings.image_configured:
        try:
            from huggingface_hub import InferenceClient

            client = InferenceClient(
                model=settings.image_model,
                token=settings.huggingface_api_key,
                provider="hf-inference",
                timeout=settings.image_timeout,
            )
            generated = client.text_to_image(
                prompt,
                width=1024,
                height=576,
                guidance_scale=7.0,
                negative_prompt=negative_prompt,
            )
            saved_path = _save_generated_image(generated, output_dir, panel_number)
            relative = f"/static/panels/{saved_path.name}"
            return ImageResult(path=saved_path, url=relative, generated=True)
        except Exception as exc:  # Provider outages must not break the full comic workflow.
            logger.exception("Hugging Face image generation failed for panel %s: %s", panel_number, exc)
            error = str(exc)
    else:
        error = "HUGGINGFACE_API_KEY is not configured."
        logger.info("Using a Pillow placeholder for panel %s: %s", panel_number, error)

    try:
        fallback = _create_placeholder(panel_number, output_dir)
        return ImageResult(
            path=fallback,
            url=f"/static/panels/{fallback.name}",
            generated=False,
            error=error,
        )
    except Exception:
        logger.exception("Could not create Pillow placeholder for panel %s", panel_number)
        raise
