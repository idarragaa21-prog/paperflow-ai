from __future__ import annotations

from app.services.clinical.citations_gate import ensure_fuentes_per_section


def test_citations_gate_inserts_fuentes_when_missing():
    md = """## Resumen ejecutivo

Texto.

## Evaluación diagnóstica

Más texto.

## Referencias

1. x
"""

    fixed, warnings = ensure_fuentes_per_section(md)
    assert "Fuentes:" in fixed
    assert len(warnings) >= 1


def test_citations_gate_does_not_touch_references_section():
    md = """## Resumen ejecutivo
Fuentes: [PUBMED:PMID:1]

## Referencias
Fuentes: should not be required here
"""
    fixed, warnings = ensure_fuentes_per_section(md)
    assert fixed == md
    assert warnings == []
