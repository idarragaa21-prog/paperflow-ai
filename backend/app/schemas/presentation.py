from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreatePresentationRequest(BaseModel):
    project_id: UUID
    topic: str = Field(..., min_length=3)
    duration_minutes: int = Field(..., ge=1, le=240)
    audience: str = Field(..., min_length=2)
    paper_ids: list[UUID] = []

    # Presentation sizing
    num_slides: int = Field(default=35, ge=20, le=50)


class CreatePresentationResponse(BaseModel):
    rq_job_id: str
