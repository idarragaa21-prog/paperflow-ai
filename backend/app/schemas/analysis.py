from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rows: list[dict] = Field(default_factory=list)


class DatasetColumnResponse(BaseModel):
    name: str
    data_type: str
    position: int
    is_nullable: bool
    summary_json: dict | None


class DatasetResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    source_type: str
    row_count: int
    column_count: int
    columns: list[DatasetColumnResponse]


class AnalysisRunCreate(BaseModel):
    project_id: UUID
    dataset_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    analysis_type: str = Field(min_length=1, max_length=64)
    input_params: dict = Field(default_factory=dict)


class AnalysisArtifactResponse(BaseModel):
    id: UUID
    artifact_type: str
    filename: str
    file_path: str
    mime_type: str
    metadata_json: dict | None


class AnalysisRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    dataset_id: UUID | None
    title: str
    analysis_type: str
    status: str
    input_params: dict | None
    runtime_metadata: dict | None
    script_text: str | None
    warnings: list[str]
    result_summary: dict | None
    engine_version: str | None
    artifact_manifest: list[dict] = Field(default_factory=list)
    artifacts: list[AnalysisArtifactResponse]
