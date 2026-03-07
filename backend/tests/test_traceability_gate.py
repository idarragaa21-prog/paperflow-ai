from __future__ import annotations

from app.services.clinical.traceability_gate import enforce_claim_traceability


def test_traceability_gate_marks_uncited_claim_bullets():
    md = """- Recomendar cirugía en todos los casos
- Definición básica
Fuentes: (No encontrado / evidencia insuficiente)
"""

    fixed, warnings = enforce_claim_traceability(md, core_papers=[])
    assert "Evidencia insuficiente para esta afirmación" in fixed
    assert warnings


def test_traceability_gate_can_append_core_evidence_line_when_no_citations():
    core = [
        {"pmid": "123", "pub_year": 2022, "publication_types": ["Practice Guideline"]},
        {"pmid": "456", "pub_year": 2020, "publication_types": ["Systematic Review"]},
    ]
    md = """## Tratamiento
- Primera línea: reposo
Fuentes: (No encontrado / evidencia insuficiente)
"""

    fixed, _warnings = enforce_claim_traceability(md, core_papers=core)
    assert "Evidencia central (artículos):" in fixed
    assert "PMID:123" in fixed
