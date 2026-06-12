"""Export a drafted manuscript to a Word (.docx) file."""
from __future__ import annotations

import io
import re

from .manuscript import SECTIONS

_SECTION_TITLES_ES = {
    "abstract": "Resumen", "introduction": "Introducción", "methods": "Métodos",
    "results": "Resultados", "discussion": "Discusión", "limitations": "Limitaciones",
    "conclusion": "Conclusión",
}


def _add_runs(paragraph, text: str) -> None:
    """Add text to a paragraph, rendering **bold** segments."""
    for i, seg in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not seg:
            continue
        run = paragraph.add_run(seg)
        if i % 2 == 1:
            run.bold = True


def _add_markdown(doc, text: str) -> None:
    for raw in (text or "").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.lstrip().startswith(("- ", "* ")):
            p = doc.add_paragraph(style="List Bullet")
            _add_runs(p, line.lstrip()[2:].strip())
        else:
            _add_runs(doc.add_paragraph(), line)


def manuscript_docx(sections: dict, *, facts: str | None = None) -> bytes:
    from docx import Document  # imported lazily so the package is optional
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    title = (sections.get("title") or "Manuscrito").strip()
    doc.add_heading(title, level=0)

    for sec in SECTIONS:
        if sec == "title":
            continue
        body = (sections.get(sec) or "").strip()
        if not body:
            continue
        doc.add_heading(_SECTION_TITLES_ES.get(sec, sec.capitalize()), level=1)
        _add_markdown(doc, body)

    if facts:
        doc.add_page_break()
        doc.add_heading("Anexo: cifras verificadas", level=1)
        for line in facts.split("\n"):
            if line.strip():
                doc.add_paragraph(line.strip())

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
