"""PDF export for complete five-panel comics."""
from __future__ import annotations

import logging
import unicodedata
from pathlib import Path

from fpdf import FPDF

from app.config import EXPORTS_DIR, PANELS_DIR, settings
from app.models import ComicDocument
from app.utils.helpers import ensure_project_dirs, safe_filename

logger = logging.getLogger(__name__)


def _font_candidate() -> Path | None:
    candidates = []
    if settings.pdf_font_path:
        candidates.append(Path(settings.pdf_font_path).expanduser())
    candidates.extend(
        [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/Arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
        ]
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _safe_core_font_text(text: str) -> str:
    """FPDF core fonts are latin-1; transliterate only when no Unicode TTF is available."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("latin-1", errors="replace").decode("latin-1")


class ComicPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("ComicCraft" if getattr(self, "unicode_font", False) else "Helvetica", size=8)
        self.set_text_color(105, 105, 105)
        self.cell(0, 7, f"ComicCraft  ·  {self.page_no()}/5", align="C")


def save_pdf(comic: ComicDocument, export_dir: Path | None = None) -> Path:
    """Save each panel on its own clean A4 page and return the absolute PDF path."""
    export_dir = export_dir or EXPORTS_DIR
    ensure_project_dirs(export_dir)
    pdf = ComicPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    font_path = _font_candidate()
    pdf.unicode_font = bool(font_path)
    if font_path:
        try:
            pdf.add_font("ComicCraft", "", str(font_path))
            pdf.add_font("ComicCraft", "B", str(font_path))
        except Exception as exc:
            logger.warning("Could not load Unicode PDF font %s: %s", font_path, exc)
            pdf.unicode_font = False
    family = "ComicCraft" if pdf.unicode_font else "Helvetica"

    for panel in comic.panels:
        pdf.add_page()
        pdf.set_fill_color(53, 89, 232)
        pdf.rect(12, 12, 186, 13, style="F")
        pdf.set_xy(16, 14)
        pdf.set_font(family, "B", 10)
        title = f"PANEL {panel.panel_number}  /  {panel.title}"
        pdf.set_text_color(255, 255, 255)
        pdf.cell(178, 8, title if pdf.unicode_font else _safe_core_font_text(title))
        pdf.set_text_color(30, 32, 36)

        image_path = PANELS_DIR / Path(panel.image_url).name
        if image_path.is_file():
            try:
                pdf.image(str(image_path), x=16, y=31, w=178, h=100)
            except Exception as exc:
                logger.warning("Skipping unreadable image in panel %s: %s", panel.panel_number, exc)
        pdf.set_xy(16, 138)
        pdf.set_font(family, "B", 13)
        if panel.caption:
            caption = panel.caption if pdf.unicode_font else _safe_core_font_text(panel.caption)
            pdf.multi_cell(178, 7, caption)
        pdf.ln(2)
        pdf.set_font(family, "", 10)
        narration = panel.narration if pdf.unicode_font else _safe_core_font_text(panel.narration)
        pdf.multi_cell(178, 6, narration)
        pdf.ln(3)
        for line in panel.dialogue:
            pdf.set_font(family, "B", 9)
            speaker = line.character if pdf.unicode_font else _safe_core_font_text(line.character)
            pdf.cell(0, 6, f"{speaker}:")
            pdf.ln(5)
            pdf.set_font(family, "", 10)
            spoken = line.text if pdf.unicode_font else _safe_core_font_text(line.text)
            pdf.multi_cell(178, 6, f'“{spoken}”' if pdf.unicode_font else f'"{spoken}"')
            pdf.ln(1)

    filename = safe_filename("comiccraft_comic", ".pdf")
    destination = export_dir / filename
    pdf.output(str(destination))
    return destination
