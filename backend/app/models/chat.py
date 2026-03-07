from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_type: Mapped[str] = mapped_column(String(32), server_default="chat", nullable=False)
    runtime_mode: Mapped[str] = mapped_column(String(32), server_default="local_only", nullable=False)
    grounded: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="chat_sessions")
    paper = relationship("Paper", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(16), server_default="resumen", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    grounded: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User", back_populates="chat_messages")
    retrieved_chunks = relationship("RetrievedChunk", back_populates="message", cascade="all, delete-orphan")
    answer_citations = relationship("AnswerCitation", back_populates="message", cascade="all, delete-orphan")


class RetrievedChunk(Base, TimestampMixin):
    __tablename__ = "retrieved_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    paper_chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_chunks.id", ondelete="SET NULL"), nullable=True)

    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)

    message = relationship("ChatMessage", back_populates="retrieved_chunks")


class AnswerCitation(Base, TimestampMixin):
    __tablename__ = "answer_citations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    paper_chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_chunks.id", ondelete="SET NULL"), nullable=True)

    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)

    message = relationship("ChatMessage", back_populates="answer_citations")


class PaperHighlight(Base, TimestampMixin):
    __tablename__ = "paper_highlights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    color: Mapped[str] = mapped_column(String(32), server_default="yellow", nullable=False)
    note_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    quoted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    paper = relationship("Paper", back_populates="highlights")
    user = relationship("User", back_populates="highlights")


Index("idx_chat_sessions_project", ChatSession.project_id)
Index("idx_chat_sessions_paper", ChatSession.paper_id)
Index("idx_chat_messages_session", ChatMessage.session_id)
Index("idx_paper_highlights_paper", PaperHighlight.paper_id)
