from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SummarizeNoteRequest(BaseModel):
    paper_id: UUID
    custom_instructions: str | None = None


class NoteCreate(BaseModel):
    project_id: UUID
    title: str
    content: str
    note_type: str = "general"
    paper_id: UUID | None = None


class NotePatch(BaseModel):
    title: str | None = None
    content: str | None = None
    note_type: str | None = None


class NoteResponse(BaseModel):
    id: UUID
    project_id: UUID
    paper_id: UUID | None
    title: str
    content: str
    note_type: str
    llm_model: str | None = None
    llm_usage: dict | None = None


class NoteListItem(BaseModel):
    id: UUID
    title: str
    note_type: str
    created_at: str | None = None
