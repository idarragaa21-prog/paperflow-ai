from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PaperDownloadRequest(BaseModel):
    project_id: UUID
    doi: str | None = Field(default=None, max_length=255)
    pmid: str | None = Field(default=None, max_length=64)
    title: str | None = None
    oa_url: str | None = None


class PaperDownloadTraceResponse(BaseModel):
    title: str
    paper_id: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    source_provider: str | None = None
    oa_url: str | None = None
    landing_url: str | None = None
    resolved_url: str | None = None
    used_fallback: bool = False
    final_status: Literal["downloaded", "existing", "unavailable", "failed"]
    failure_reason: str | None = None
    audited_at: str | None = None


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
    is_processed: bool = False
    processing_status: str = "uploaded"
    duplicate: bool = False
    download_trace: PaperDownloadTraceResponse | None = None


class PaperDetailResponse(PaperRecordResponse):
    authors: str | None = None
    favorite: bool = False
    full_text_extracted: str | None = None
    processing_error: str | None = None
    processing_warnings: list[str] = Field(default_factory=list)
    downloaded_at: str | None = None
    created_at: str | None = None


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


class BatchDownloadTraceItemResponse(BaseModel):
    title: str
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    paper_id: str | None = None
    source_provider: str | None = None
    oa_url: str | None = None
    landing_url: str | None = None
    resolved_url: str | None = None
    used_fallback: bool = False
    final_status: Literal["downloaded", "existing", "unavailable", "failed"]
    failure_reason: str | None = None


class BatchDownloadOutputResponse(BaseModel):
    items: list[BatchDownloadTraceItemResponse] = Field(default_factory=list)
    downloaded: list[BatchDownloadTraceItemResponse] = Field(default_factory=list)
    already_exists: list[BatchDownloadTraceItemResponse] = Field(default_factory=list)
    not_available: list[BatchDownloadTraceItemResponse] = Field(default_factory=list)
    failed: list[BatchDownloadTraceItemResponse] = Field(default_factory=list)


PaperRecordResponse.model_rebuild()
PaperDetailResponse.model_rebuild()
