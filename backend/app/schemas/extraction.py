from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ExtractionTemplateResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    discipline: str | None
    is_builtin: bool
    schema_json: dict


class ExtractionRecordCreate(BaseModel):
    project_id: UUID
    paper_id: UUID | None = None
    template_id: UUID | None = None


class ExtractionFieldPatch(BaseModel):
    value_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_page: int | None = None
    source_locator: dict | None = None


class ExtractionRecordPatch(BaseModel):
    status: str | None = None
    fields: dict[str, ExtractionFieldPatch] = Field(default_factory=dict)


class ExtractionFieldValueResponse(BaseModel):
    id: UUID
    field_name: str
    value_text: str | None
    auto_value_text: str | None
    confidence: float
    source_page: int | None
    source_locator: dict | None
    manually_edited: bool
    candidate_spans: list[dict] = Field(default_factory=list)
    validation_issues: list[str] = Field(default_factory=list)


class ExtractionRecordResponse(BaseModel):
    id: UUID
    project_id: UUID
    paper_id: UUID | None
    template_id: UUID
    status: str
    version: int
    summary_json: dict | None
    template_version: str | None = None
    fields: list[ExtractionFieldValueResponse]
