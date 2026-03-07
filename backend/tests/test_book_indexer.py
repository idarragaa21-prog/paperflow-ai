from __future__ import annotations

from pathlib import Path

from app.services.books.indexer import index_book_pdf


def test_book_index_creation(tmp_path: Path):
    # Create a tiny PDF with headings using reportlab
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "book.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Chapter 1 Osteotomia")
    c.setFont("Helvetica", 12)
    c.drawString(72, 690, "Osteotomia tibial proximal tecnica y complicaciones")
    c.showPage()
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Chapter 2 Fracturas por estres")
    c.setFont("Helvetica", 12)
    c.drawString(72, 690, "Diagnostico diferencial y retorno al deporte")
    c.save()

    out = index_book_pdf(pdf_path)
    assert out["total_pages"] == 2
    assert isinstance(out.get("chapters"), list)
    assert len(out["chapters"]) >= 1
    # keywords exist
    assert isinstance(out["chapters"][0].get("keywords"), list)
