"""Browser pages and JSON endpoints for ComicCraft."""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.config import EXPORTS_DIR, PANELS_DIR, PROJECT_ROOT, settings
from app.models import ComicAPIResponse, ComicDocument, ComicRequest
from app.services.demo_generator import generate_demo_outline, generate_demo_story
from app.services.exporters import save_pdf
from app.services.gemini_flash import generate_outline
from app.services.gemini_pro import generate_story
from app.services.image_generator import ImageResult, generate_image
from app.services.layout_builder import build_comic_layout
from app.utils.helpers import ensure_project_dirs, truncate_text

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))
_COMIC_STORE: dict[str, ComicDocument] = {}
_STORE_LOCK = threading.RLock()


def _home_context(request: Request) -> dict:
    return {
        "request": request,
        "gemini_configured": settings.gemini_configured,
        "image_configured": settings.image_configured,
    }


def _save_comic(comic: ComicDocument) -> None:
    with _STORE_LOCK:
        _COMIC_STORE[comic.id] = comic


def _get_comic(comic_id: str) -> ComicDocument | None:
    with _STORE_LOCK:
        return _COMIC_STORE.get(comic_id)


def _generate_comic(payload: ComicRequest) -> ComicDocument:
    """Run the full pipeline; fall back to deterministic text and placeholder images."""
    ai_mode = "gemini"
    ai_notice = ""
    try:
        outline = generate_outline(payload)
        story = generate_story(
            outline,
            character_name=payload.character_name,
            setting=payload.setting,
            tone=payload.tone,
            art_style=payload.art_style,
        )
    except Exception as exc:
        # Log diagnostic detail locally; show a friendly, actionable message in the UI.
        logger.warning("Using built-in demo story because Gemini generation is unavailable: %s", exc)
        outline = generate_demo_outline(payload)
        story = generate_demo_story(outline, payload)
        ai_mode = "demo"
        if settings.gemini_configured:
            ai_notice = "Gemini could not complete this request, so a built-in demo story is shown. Check your model access or API key."
        else:
            ai_notice = "Demo story mode is active. Add a Gemini API key in .env to generate original AI stories."

    images: list[ImageResult] = []
    for outline_panel in outline.panels:
        result = generate_image(
            outline_panel.image_prompt,
            panel_number=outline_panel.panel_number,
            art_style=payload.art_style,
            character_name=payload.character_name,
            output_dir=PANELS_DIR,
        )
        images.append(result)

    panels = build_comic_layout(story, images)
    image_count = sum(1 for image in images if image.generated)
    if image_count == 5:
        image_notice = "All five illustrations were generated with the configured image provider."
    elif image_count:
        image_notice = f"{image_count} of 5 illustrations were AI-generated; the remaining panels use local placeholders."
    elif settings.image_configured:
        image_notice = "The image provider was unavailable. Pillow placeholders keep the comic preview and PDF complete."
    else:
        image_notice = "Image generation unavailable. Add a Hugging Face token to generate illustrations; placeholder images keep demo mode working."

    comic = ComicDocument(
        title=f"{payload.character_name}'s {payload.tone.title()} Comic",
        request=payload,
        panels=panels,
        ai_mode=ai_mode,
        ai_notice=ai_notice,
        image_notice=image_notice,
    )
    _save_comic(comic)
    return comic


@router.get("/", name="home")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=_home_context(request),
    )


@router.post("/generate", name="generate_comic_form")
async def generate_comic_form(
    request: Request,
    story_prompt: str = Form(default=""),
    character_name: str = Form(default=""),
    setting: str = Form(default=""),
    tone: str = Form(default=""),
    art_style: str = Form(default=""),
):
    try:
        payload = ComicRequest(
            story_prompt=story_prompt,
            character_name=character_name,
            setting=setting,
            tone=tone,
            art_style=art_style,
        )
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}"
            for issue in exc.errors()
        )
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"request": request, "message": f"Please check the form fields. {errors}"},
            status_code=422,
        )
    try:
        comic = await run_in_threadpool(_generate_comic, payload)
        return templates.TemplateResponse(
            request=request,
            name="comic_preview.html",
            context={"request": request, "comic": comic},
        )
    except Exception:
        logger.exception("Comic generation failed unexpectedly")
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "request": request,
                "message": "We couldn't assemble this comic. Please try again; no API key is needed for demo mode.",
            },
            status_code=500,
        )


@router.get("/preview/{comic_id}", name="comic_preview")
def comic_preview(request: Request, comic_id: str):
    comic = _get_comic(comic_id)
    if not comic:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"request": request, "message": "That comic is no longer in this session. Create a new one to continue."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request=request,
        name="comic_preview.html",
        context={"request": request, "comic": comic},
    )


@router.post("/export/{comic_id}", name="export_comic")
async def export_comic(comic_id: str):
    comic = _get_comic(comic_id)
    if not comic:
        return RedirectResponse(url="/?error=missing-comic", status_code=303)
    try:
        pdf_path = await run_in_threadpool(save_pdf, comic)
        comic.pdf_filename = pdf_path.name
        _save_comic(comic)
        return RedirectResponse(url=f"/export-success?file={pdf_path.name}", status_code=303)
    except Exception:
        logger.exception("PDF export failed for comic %s", comic_id)
        return RedirectResponse(url="/?error=export-failed", status_code=303)


@router.get("/export-success", name="export_success")
def export_success(request: Request, file: str = ""):
    filename = Path(file).name if file else ""
    file_path = EXPORTS_DIR / filename
    valid = bool(filename and filename.endswith(".pdf") and file_path.is_file())
    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={
            "request": request,
            "file_url": f"/static/exports/{filename}" if valid else "",
            "file_name": filename if valid else "",
            "export_ready": valid,
        },
    )


@router.post("/generate-comic/json", response_model=ComicAPIResponse, name="generate_comic_json")
async def generate_comic_json(payload: ComicRequest):
    comic = await run_in_threadpool(_generate_comic, payload)
    pdf_path = await run_in_threadpool(save_pdf, comic)
    comic.pdf_filename = pdf_path.name
    _save_comic(comic)
    return ComicAPIResponse(
        comic_id=comic.id,
        title=comic.title,
        panels=comic.panels,
        ai_mode=comic.ai_mode,
        ai_notice=comic.ai_notice,
        image_notice=comic.image_notice,
        pdf_url=f"/static/exports/{pdf_path.name}",
    )


@router.post("/test-image", name="test_image")
async def test_image(
    prompt: str = Form(default="A friendly fox discovers a lantern in an enchanted forest."),
    panel_number: int = Form(default=1, ge=1, le=5),
    art_style: str = Form(default="comic book illustration"),
):
    result = await run_in_threadpool(
        generate_image,
        prompt,
        panel_number,
        art_style,
        "the main character",
        PANELS_DIR,
    )
    return JSONResponse(
        {
            "image_url": result.url,
            "generated": result.generated,
            "status": "generated" if result.generated else "placeholder",
            "message": "Image generation unavailable" if not result.generated else "AI illustration generated.",
        }
    )


@router.get("/api/status", name="api_status")
def api_status() -> dict[str, object]:
    return {
        "status": "ok",
        "gemini_configured": settings.gemini_configured,
        "image_provider": settings.image_provider,
        "image_configured": settings.image_configured,
        "demo_mode_available": True,
        "panels_per_comic": 5,
    }


@router.get("/manus-routes.json", include_in_schema=False)
def route_manifest():
    manifest = PROJECT_ROOT / "static" / "manus-routes.json"
    return FileResponse(manifest, media_type="application/json")
