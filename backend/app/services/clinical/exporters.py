from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from app.core.storage import storage_manager


def export_docx(*, user_id: UUID, sheet_id: UUID, version: int, topic: str, content_markdown: str) -> str:
    """Export sheet to DOCX. Returns relative path under storage base_dir."""

    from docx import Document

    text = re.sub(r"\n{3,}", "\n\n", (content_markdown or "").strip())

    doc = Document()
    doc.add_heading(topic, level=1)
    for para in text.split("\n\n"):
        doc.add_paragraph(para)

    rel_dir = Path("clinical_exports") / str(user_id) / str(sheet_id)
    abs_dir = (storage_manager.base_dir / rel_dir).resolve()
    abs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"clinical_{sheet_id}_v{int(version)}.docx"
    abs_path = (abs_dir / filename).resolve()
    abs_path.relative_to(storage_manager.base_dir)
    doc.save(str(abs_path))

    return str(abs_path.relative_to(storage_manager.base_dir))


def export_pdf(*, user_id: UUID, sheet_id: UUID, version: int, topic: str, content_markdown: str) -> str:
    """Export sheet to a simple PDF. Returns relative path under storage base_dir."""

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    text = re.sub(r"\n{3,}", "\n\n", (content_markdown or "").strip())

    rel_dir = Path("clinical_exports") / str(user_id) / str(sheet_id)
    abs_dir = (storage_manager.base_dir / rel_dir).resolve()
    abs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"clinical_{sheet_id}_v{int(version)}.pdf"
    abs_path = (abs_dir / filename).resolve()
    abs_path.relative_to(storage_manager.base_dir)

    c = canvas.Canvas(str(abs_path), pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, topic[:120])
    y -= 28
    c.setFont("Helvetica", 10)

    for line in text.splitlines():
        if y < 72:
            c.showPage()
            y = height - 72
            c.setFont("Helvetica", 10)
        c.drawString(72, y, (line[:160] if line else ""))
        y -= 12

    c.save()

    return str(abs_path.relative_to(storage_manager.base_dir))
