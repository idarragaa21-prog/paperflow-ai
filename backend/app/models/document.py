from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class PaperFile(Base, TimestampMixin):
    __tablename__ = "paper_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), server_default="application/pdf", nullable=False)
    size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    paper = relationship("Paper", back_populates="files")


class PaperParseRun(Base, TimestampMixin):
    __tablename__ = "paper_parse_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(32), server_default="queued", nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), server_default="paperflow_pdf_v1", nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), server_default="1", nullable=False)
    used_ocr: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    pages_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chars_extracted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warnings: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    paper = relationship("Paper", back_populates="parse_runs")
    chunks = relationship("PaperChunk", back_populates="parse_run", cascade="all, delete-orphan")
    citation_spans = relationship("PaperCitationSpan", back_populates="parse_run", cascade="all, delete-orphan")


class PaperChunk(Base, TimestampMixin):
    __tablename__ = "paper_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    parse_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_parse_runs.id", ondelete="CASCADE"), nullable=False)

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    paper = relationship("Paper", back_populates="chunks")
    parse_run = relationship("PaperParseRun", back_populates="chunks")


class PaperCitationSpan(Base, TimestampMixin):
    __tablename__ = "paper_citation_spans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    parse_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_parse_runs.id", ondelete="CASCADE"), nullable=False)

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)

    paper = relationship("Paper", back_populates="citation_spans")
    parse_run = relationship("PaperParseRun", back_populates="citation_spans")


Index("idx_paper_files_paper", PaperFile.paper_id)
Index("idx_parse_runs_paper", PaperParseRun.paper_id)
Index("idx_paper_chunks_paper_page", PaperChunk.paper_id, PaperChunk.page_number)
Index("idx_paper_citations_paper_page", PaperCitationSpan.paper_id, PaperCitationSpan.page_number)
