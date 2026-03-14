from __future__ import annotations

import pytest

from app.services.extraction_service import _validate_field, export_records, universal_template_schema


def test_universal_template_is_versioned():
    schema = universal_template_schema()
    assert schema["version"] == "universal-study-template.v1"


def test_validate_field_rejects_invalid_sample_and_year():
    assert _validate_field("sample", "ten") == ["invalid_sample_size"]
    assert _validate_field("year", "1899") == ["invalid_year"]
    assert _validate_field("design", "cohort") == []


def test_export_records_requires_data():
    with pytest.raises(ValueError, match="No extraction records available for export"):
        export_records([], "csv")
