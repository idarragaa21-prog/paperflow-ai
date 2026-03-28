from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


MembershipRole = Literal["owner", "editor", "viewer"]


class ProjectMemberInviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: MembershipRole = "viewer"


class ProjectMemberUpdateRequest(BaseModel):
    role: MembershipRole


class ProjectMemberResponse(BaseModel):
    id: UUID | None = None
    project_id: UUID
    user_id: UUID
    email: str
    full_name: str | None = None
    role: MembershipRole
    created_at: datetime | None = None
