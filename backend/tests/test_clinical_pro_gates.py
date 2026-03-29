from __future__ import annotations

from app.schemas.clinical_pro import ClinicalProOutput, ClinicalProQuality, ClinicalProSection
from app.services.clinical.pro_gates import gate_min_assets, gate_min_evidence_map


def _base_output() -> ClinicalProOutput:
    return ClinicalProOutput(
        title="ACL",
        sections=[ClinicalProSection(id="resumen", title="Resumen", content_markdown="Fuentes: (No encontrado / evidencia insuficiente)")],
        quality=ClinicalProQuality(evidence_strength="low", gaps=[]),
    )


def test_gate_min_evidence_map_marks_degraded_fallback():
    fixed, warnings = gate_min_evidence_map(_base_output())

    assert warnings == ["Evidence map missing; inserted explicit degraded fallback row."]
    assert fixed.evidence_map[0]["conclusion"] == "No encontrado / evidencia insuficiente"
    assert "evidence_map_missing" in fixed.quality.gaps
    assert "evidence_map_degraded_fallback" in fixed.quality.gaps


def test_gate_min_assets_inserts_explicit_degraded_assets():
    fixed, warnings = gate_min_assets(_base_output())

    assert any("degraded fallback tables" in warning for warning in warnings)
    assert any("degraded fallback charts" in warning for warning in warnings)
    assert any(table.title.startswith("Tabla de apoyo (fallback degradado") for table in fixed.tables)
    assert any(chart.note and "Fallback degradado" in chart.note for chart in fixed.charts)
    assert any(figure.title == "Mapa conceptual (fallback degradado)" for figure in fixed.mermaid)
    assert "tables_degraded_fallback" in fixed.quality.gaps
    assert "charts_degraded_fallback" in fixed.quality.gaps
