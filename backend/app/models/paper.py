from __future__ import annotations

import sqlalchemy as sa

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class Paper(Base, TimestampMixin):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    search_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("search_results.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)

    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pmid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pmcid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    journal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    abstract_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_open_access: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    oa_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    favorite: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    is_processed: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    full_text_extracted: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), server_default="uploaded", nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_warnings: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="papers")
    files = relationship("PaperFile", back_populates="paper", cascade="all, delete-orphan")
    parse_runs = relationship("PaperParseRun", back_populates="paper", cascade="all, delete-orphan")
    chunks = relationship("PaperChunk", back_populates="paper", cascade="all, delete-orphan")
    citation_spans = relationship("PaperCitationSpan", back_populates="paper", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="paper", cascade="all, delete-orphan")
    highlights = relationship("PaperHighlight", back_populates="paper", cascade="all, delete-orphan")
    extraction_records = relationship("ExtractionRecord", back_populates="paper", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "content_hash", name="uq_papers_project_hash"),
    )


Index("idx_papers_project", Paper.project_id)
Index("idx_papers_hash", Paper.content_hash)
