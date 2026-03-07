from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DraftCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=255)


class DraftPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = None


class GenerateDraftSectionRequest(BaseModel):
    heading: str = Field(min_length=1, max_length=255)
    paper_ids: list[UUID] = Field(default_factory=list)
    extraction_record_ids: list[UUID] = Field(default_factory=list)


class ResolveDraftCitationsRequest(BaseModel):
    section_id: UUID | None = None


class DraftCitationResponse(BaseModel):
    id: UUID
    marker: str
    quoted_text: str | None
    locator: dict | None
    confidence: float
    reference_item_id: UUID | None
    paper_citation_span_id: UUID | None


class DraftSectionResponse(BaseModel):
    id: UUID
    heading: str
    position: int
    content: str
    generated_with_model: str | None
    confidence: float
    citations: list[DraftCitationResponse]


class DraftResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    status: str
    version: int
    sections: list[DraftSectionResponse]


class EvidenceTableResponse(BaseModel):
    id: UUID
    title: str
    table_json: dict
    confidence: float
