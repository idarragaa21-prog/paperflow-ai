from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=3)
    session_id: UUID | None = None
    task_type: str = Field(default="chat")
    max_citations: int = Field(default=3, ge=1, le=8)


class HighlightCreate(BaseModel):
    color: str = Field(default="yellow", max_length=32)
    note_text: str | None = None
    quoted_text: str | None = None
    locator: dict | None = None


class ChatCitationResponse(BaseModel):
    paper_id: UUID
    page: int | None
    locator: dict | None
    quoted_text: str


class ChatResponse(BaseModel):
    session_id: UUID
    answer: str
    claim_type: str
    confidence: float
    grounded: bool
    citations: list[ChatCitationResponse]
    blocked_reason: str | None = None
    model_name: str | None = None
    grounding_score: float | None = None
    retrieval_debug: list[dict] | None = None


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    claim_type: str
    confidence: float
    grounded: bool
    created_at: str | None
    citations: list[ChatCitationResponse]


class ChatSessionResponse(BaseModel):
    id: UUID
    project_id: UUID
    paper_id: UUID | None
    title: str | None
    runtime_mode: str
    grounded: bool
    messages: list[ChatMessageResponse]
