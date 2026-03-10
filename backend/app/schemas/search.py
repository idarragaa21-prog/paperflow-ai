from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    year_from: int | None = None
    year_to: int | None = None
    open_access_only: bool = False
    journal: str | None = None
    source: str | None = None


class SearchOpenTarget(BaseModel):
    kind: str
    url: str
    label: str


class SearchRequest(BaseModel):
    project_id: UUID
    query: str = Field(..., min_length=3)
    max_results: int = Field(20, ge=1, le=100)
    filters: SearchFilters | None = None


class PaperMetadata(BaseModel):
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None

    title: str
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    pub_year: int | None = None
    abstract: str | None = None
    source: str | None = None
    language: str | None = None

    is_open_access: bool = False
    oa_url: str | None = None
    has_abstract: bool = False
    can_save_pdf: bool = False
    can_open_external: bool = False
    content_state: str = "metadata_only"
    open_targets: list[SearchOpenTarget] = Field(default_factory=list)


class SearchResponse(BaseModel):
    count: int
    results: list[PaperMetadata]
    query_translation: str | None = None
    cached: bool = False
    sources: list[str] = Field(default_factory=list)
    partial_success: bool = False
    provider_status: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SearchRecordResponse(BaseModel):
    id: UUID
    project_id: UUID
    query: str
    source: str
    results_count: int | None
    executed_at: Any | None
