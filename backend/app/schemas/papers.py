from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class PaperDownloadRequest(BaseModel):
    project_id: UUID

    # At least one of doi, pmid, or oa_url must be provided.
    # oa_url alone is valid for DOAJ papers that lack DOI/PMID.
    doi: str | None = Field(default=None, max_length=255)
    pmid: str | None = Field(default=None, max_length=64)

    title: str | None = None

    # If the search result already resolved an OA URL, pass it here
    # so the backend uses it as first priority instead of re-resolving.
    oa_url: str | None = None


class PaperRecordResponse(BaseModel):
    id: UUID
    project_id: UUID

    title: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    journal: str | None = None
    publication_year: int | None = None
    language: str | None = None
    abstract_text: str | None = None
    source_provider: str | None = None
    source_type: str | None = None
    is_open_access: bool = False
    oa_url: str | None = None

    filename: str
    file_path: str
    file_size_kb: int | None = None
    content_hash: str
    processing_status: str = "uploaded"

    duplicate: bool = False

    # Download traceability fields — populated on fresh downloads only, None on duplicates.
    used_fallback: bool | None = None
    oa_url_provided: str | None = None


class PaperDeleteResponse(BaseModel):
    ok: bool


class BatchDownloadPaperRef(BaseModel):
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    title: str | None = None
    oa_url: str | None = None


class PapersBatchDownloadRequest(BaseModel):
    project_id: UUID
    papers: list[BatchDownloadPaperRef] = Field(default_factory=list)
