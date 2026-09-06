from __future__ import annotations

import json
import re
import sys
import textwrap
import time
from pathlib import Path

from deep_translator import GoogleTranslator
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


SOURCE = Path("/Users/hepded/Downloads/Telegram Desktop/IT.pdf")
OUT_DIR = Path("/Users/hepded/Desktop/tg bot")
CACHE = OUT_DIR / "IT_ru_pages.json"
OUT_PDF = OUT_DIR / "IT_ru_translated.pdf"


def cleaned(text: str) -> str:
    text = text.replace("\uf0c5", "⊕")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_cache() -> dict[str, str]:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, str]) -> None:
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CACHE)


def chunks(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    current = ""
    for paragraph in re.split(r"(\n\n+)", text):
        if len(current) + len(paragraph) <= limit:
            current += paragraph
        else:
            if current.strip():
                pieces.append(current.strip())
            if len(paragraph) <= limit:
                current = paragraph
            else:
                for wrapped in textwrap.wrap(paragraph, width=limit, break_long_words=False):
                    pieces.append(wrapped)
                current = ""
    if current.strip():
        pieces.append(current.strip())
    return pieces


def translate_page(translator: GoogleTranslator, text: str) -> str:
    if not text:
        return ""
    translated: list[str] = []
    for part in chunks(text):
        for attempt in range(5):
            try:
                translated.append(translator.translate(part))
                break
            except Exception as exc:
                if attempt == 4:
                    raise RuntimeError(f"Translation failed after retries: {exc}") from exc
                time.sleep(1.5 * (attempt + 1))
        time.sleep(0.08)
    return "\n\n".join(translated)


def extract_pages() -> list[str]:
    reader = PdfReader(str(SOURCE))
    return [cleaned(page.extract_text() or "") for page in reader.pages]


def register_font() -> str:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            pdfmetrics.registerFont(TTFont("RusFont", candidate))
            return "RusFont"
    return "Helvetica"


def build_pdf(pages: list[str], font_name: str) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SlideTitle",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "BodyRus",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6,
    )
    note_style = ParagraphStyle(
        "Note",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#6b7280"),
    )

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=landscape(A4),
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title="IT - перевод на русский",
        author="Codex",
    )

    story = []
    for index, text in enumerate(pages, start=1):
        story.append(Paragraph(f"Страница {index}", title_style))
        story.append(Paragraph("Перевод с английского на русский", note_style))
        story.append(Spacer(1, 0.25 * cm))
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for paragraph in safe_text.splitlines():
            if paragraph.strip():
                story.append(Paragraph(paragraph.strip(), body_style))
            else:
                story.append(Spacer(1, 0.12 * cm))
        if index != len(pages):
            story.append(PageBreak())

    doc.build(story)


def main() -> int:
    pages = extract_pages()
    cache = load_cache()
    translator = GoogleTranslator(source="auto", target="ru")

    for index, source_text in enumerate(pages, start=1):
        key = str(index)
        if key in cache:
            continue
        print(f"Translating page {index}/{len(pages)}", flush=True)
        cache[key] = translate_page(translator, source_text)
        save_cache(cache)

    translated_pages = [cache[str(index)] for index in range(1, len(pages) + 1)]
    build_pdf(translated_pages, register_font())
    print(OUT_PDF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
