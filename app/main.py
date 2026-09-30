"""ComicCraft application entry point."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import EXPORTS_DIR, PANELS_DIR, STATIC_DIR, settings
from app.routes import router
from app.utils.helpers import ensure_project_dirs

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
ensure_project_dirs(PANELS_DIR, EXPORTS_DIR)

app = FastAPI(
    title="ComicCraft — AI Comic Story Creator",
    description="Create a connected five-panel comic with narration, dialogue, illustrations, and PDF export.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)


@app.get("/health", include_in_schema=False)
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": "ComicCraft"}
