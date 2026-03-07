from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ScreeningBatchCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=255)
    stage: str = Field(default="title_abstract")


class ScreeningDecisionCreate(BaseModel):
    batch_id: UUID
    paper_id: UUID
    decision: str = Field(pattern="^(include|exclude|maybe)$")
    stage: str = Field(default="title_abstract")
    reason_id: UUID | None = None
    notes: str | None = None


class EligibilityReasonCreate(BaseModel):
    project_id: UUID
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectCommentCreate(BaseModel):
    project_id: UUID
    body: str = Field(min_length=1)
    target_type: str | None = None
    target_id: str | None = None


class PeerReviewActionCreate(BaseModel):
    project_id: UUID
    action: str = Field(min_length=1, max_length=64)
    status: str = Field(default="open")
    payload_json: dict | None = None


class ScreeningBatchResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    stage: str
    status: str


class ScreeningDecisionResponse(BaseModel):
    id: UUID
    batch_id: UUID
    paper_id: UUID
    decision: str
    stage: str
    reason_id: UUID | None
    notes: str | None


class EligibilityReasonResponse(BaseModel):
    id: UUID
    project_id: UUID
    code: str
    label: str
    description: str | None
