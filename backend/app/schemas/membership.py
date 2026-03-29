from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


MembershipRole = Literal["owner", "editor", "viewer"]
InvitationStatus = Literal["pending", "accepted", "revoked"]


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


class ProjectInvitationResponse(BaseModel):
    id: UUID
    project_id: UUID
    email: str
    role: MembershipRole
    token: str
    accept_path: str
    status: InvitationStatus
    created_at: datetime | None = None
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None


class ProjectInviteResultResponse(BaseModel):
    kind: Literal["membership", "invitation"]
    member: ProjectMemberResponse | None = None
    invitation: ProjectInvitationResponse | None = None


class ProjectInvitationLookupResponse(BaseModel):
    id: UUID
    project_id: UUID
    project_title: str
    email: str
    role: MembershipRole
    status: InvitationStatus
    accept_path: str
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None


class ProjectInvitationAcceptResponse(BaseModel):
    ok: bool = True
    project_id: UUID
    project_title: str
    member: ProjectMemberResponse
