from __future__ import annotations

from app.services.clinical.sections import sections_for


def test_clinical_sections_focus_diagnostic_omits_treatments():
    secs = sections_for(objective="clinical_decision", focus="diagnostic")
    assert "Tratamiento conservador" not in secs
    assert "Tratamiento quirúrgico" not in secs
    assert secs[-1] == "Referencias"


def test_clinical_sections_quick_review_is_short():
    secs = sections_for(objective="quick_review", focus="complete")
    assert len(secs) <= 8
    assert secs[0] == "Resumen ejecutivo"
    assert secs[-1] == "Referencias"
