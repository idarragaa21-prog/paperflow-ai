from uuid import uuid4

from app.schemas.extraction import ExtractionTemplateResponse


def test_extraction_template_response_keeps_schema_json_wire_name() -> None:
    payload = ExtractionTemplateResponse(
        id=uuid4(),
        name="Template",
        slug="template",
        description=None,
        discipline=None,
        is_builtin=True,
        schema_json={"version": "1.0.0", "fields": []},
    )

    assert payload.schema_definition == {"version": "1.0.0", "fields": []}
    assert payload.model_dump(by_alias=True)["schema_json"] == {"version": "1.0.0", "fields": []}
