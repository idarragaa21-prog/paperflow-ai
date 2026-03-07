from __future__ import annotations

from app.services.extraction_service import _validate_field, universal_template_schema


def test_universal_template_is_versioned():
    schema = universal_template_schema()
    assert schema["version"] == "universal-study-template.v1"


def test_validate_field_rejects_invalid_sample_and_year():
    assert _validate_field("sample", "ten") == ["invalid_sample_size"]
    assert _validate_field("year", "1899") == ["invalid_year"]
    assert _validate_field("design", "cohort") == []
