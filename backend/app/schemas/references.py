from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ReferencesImportRequest(BaseModel):
    project_id: UUID
    format: str = Field(..., pattern="^(bibtex|ris)$")
    content: str = Field(..., min_length=1)


class ReferenceItemResponse(BaseModel):
    id: UUID
    project_id: UUID
    paper_id: UUID | None = None
    source_format: str
    citation_key: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    language: str | None = None


class ReferencesImportResponse(BaseModel):
    imported: int
    skipped: int
    items: list[ReferenceItemResponse] = Field(default_factory=list)
