"""Uploaded-PDF extraction: parsing (text/tables/images) and the full pipeline."""
from __future__ import annotations

import io

import pytest

pytest.importorskip("fitz")  # PyMuPDF


def _sample_pdf() -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from PIL import Image as PILImage, ImageDraw

    img = PILImage.new("RGB", (400, 240), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 10), "Figura 1. Mortalidad por grupo", fill="black")
    d.rectangle([60, 120, 110, 200], fill="#3b5bdb")
    d.rectangle([200, 60, 250, 200], fill="#888")
    ibuf = io.BytesIO(); img.save(ibuf, "PNG"); ibuf.seek(0)

    buf = io.BytesIO()
    st = getSampleStyleSheet()
    SimpleDocTemplate(buf, pagesize=A4).build([
        Paragraph("Estatinas y mortalidad: ensayo aleatorizado", st["Title"]),
        Paragraph("Ensayo en Espana, 1208 adultos, 12 meses.", st["Normal"]),
        Spacer(1, 10), Paragraph("Tabla 1. Resultados", st["Heading2"]),
        Table([["Grupo", "Eventos", "N"], ["Estatina", "42", "610"], ["Control", "88", "598"]],
              style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)])),
        Spacer(1, 14), Image(ibuf, width=300, height=180),
    ])
    return buf.getvalue()


def test_pdf_to_parts_extracts_text_table_image():
    from metaforge.pdf_extract import pdf_to_parts
    import shutil
    parts = pdf_to_parts(_sample_pdf())
    try:
        assert "Estatinas" in parts["narrative"]
        assert len(parts["tables"]) >= 1
        assert "Estatina | 42 | 610" in parts["tables"][0]
        assert len(parts["image_paths"]) >= 1
        assert parts["has_fulltext"]
    finally:
        shutil.rmtree(parts["image_dir"], ignore_errors=True)


def test_extract_pdf_pipeline(monkeypatch):
    import metaforge.extract as ex
    from metaforge import figvision

    def fake(prompt, timeout=150, model=None, cwd=None):
        if "DOS cosas" in prompt:
            return {"study": {"year": "2024", "country": "España"}, "population": {}, "arms": [],
                    "followup": "", "outcomes": []}
        if "TABLA" in prompt:
            return {"outcomes": [{"name": "Mortalidad", "type": "binary", "timepoint": "",
                                  "intervention": {"events": 42, "n": 610},
                                  "control": {"events": 88, "n": 598},
                                  "effect": {"measure": "HR", "value": 0.46, "ci_lower": 0.32, "ci_upper": 0.66}}]}
        return {"outcomes": []}

    monkeypatch.setattr(ex, "ai_available", lambda: True)
    monkeypatch.setattr(ex, "run_claude_json", fake)
    monkeypatch.setattr(figvision, "run_claude_json", lambda p, timeout=150, model=None, cwd=None: {"outcomes": []})
    out = ex.extract_pdf(_sample_pdf(), filename="estatinas_2024.pdf", mode="ai")
    assert out["source"] == "pdf" and out["study_label"] == "estatinas_2024"
    assert out["n_tables"] >= 1 and out["found"]
    assert out["data"]["study"]["country"] == "España"
    assert len(out["meta_rows"]) == 1 and out["meta_rows"][0]["a_events"] == 42.0


def test_extract_pdf_endpoint(monkeypatch):
    import metaforge.extract as ex
    from fastapi.testclient import TestClient
    from metaforge.api import app

    monkeypatch.setattr(ex, "ai_available", lambda: True)
    monkeypatch.setattr(ex, "run_claude_json",
                        lambda p, timeout=150, model=None, cwd=None: {"outcomes": [], "study": {}, "population": {}, "arms": []})
    from metaforge import figvision
    monkeypatch.setattr(figvision, "run_claude_json", lambda p, timeout=150, model=None, cwd=None: {"outcomes": []})
    c = TestClient(app)
    r = c.post("/extract/pdf", files={"file": ("x.pdf", _sample_pdf(), "application/pdf")})
    assert r.status_code == 200 and r.json()["source"] == "pdf"
    assert c.post("/extract/pdf", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 400
    assert c.post("/extract/pdf", files={"file": ("x.pdf", b"", "application/pdf")}).status_code == 400


def test_corrupt_pdf_degrades_gracefully():
    from metaforge.extract import extract_pdf
    out = extract_pdf(b"%PDF-1.4 not really a pdf", filename="broken.pdf", mode="local")
    assert out["found"] is False and out["data"] is None
    assert "No se pudo leer el PDF" in out["note"]
