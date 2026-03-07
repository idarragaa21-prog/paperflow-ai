from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    clinical_area: str | None = None
    runtime_mode: str = Field(default="local_only", pattern="^(local_only|hybrid|cloud_enabled)$")


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    clinical_area: str | None = None
    runtime_mode: str | None = Field(default=None, pattern="^(local_only|hybrid|cloud_enabled)$")


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    clinical_area: str | None
    runtime_mode: str
    archived: bool
