"""Register bundled, embedded fonts for publication PDF figures."""

from __future__ import annotations

from pathlib import Path

import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


FONT_SOURCE = Path(__file__).resolve()
_FONT_DIR = Path(reportlab.__file__).resolve().parent / "fonts"
_FONT_FILES = {
    "Helvetica": "Vera.ttf",
    "Helvetica-Bold": "VeraBd.ttf",
    "Helvetica-Oblique": "VeraIt.ttf",
}


def register_embedded_sans() -> None:
    """Replace ReportLab base-font aliases with embedded bundled TTF fonts."""

    registered = set(pdfmetrics.getRegisteredFontNames())
    for alias, filename in _FONT_FILES.items():
        if alias in registered:
            continue
        path = _FONT_DIR / filename
        if not path.is_file():
            raise RuntimeError(f"required ReportLab font is missing: {path}")
        pdfmetrics.registerFont(TTFont(alias, str(path)))
