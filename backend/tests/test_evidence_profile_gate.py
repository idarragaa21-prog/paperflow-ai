from __future__ import annotations

from app.services.clinical.evidence_profile_gate import ensure_evidence_profile_block


def test_evidence_profile_inserted_when_missing():
    md = "## Resumen ejecutivo\nFuentes: (No encontrado / evidencia insuficiente)\n"
    fixed, warnings = ensure_evidence_profile_block(md, articles_available=True, books_included=False)
    assert "Perfil de evidencia" in fixed
    assert "Basado principalmente" in fixed
    assert warnings


def test_evidence_profile_noop_when_present():
    md = "**Perfil de evidencia:** x\n\n## Resumen ejecutivo\n"
    fixed, warnings = ensure_evidence_profile_block(md, articles_available=True, books_included=True)
    assert fixed == md
    assert warnings == []
