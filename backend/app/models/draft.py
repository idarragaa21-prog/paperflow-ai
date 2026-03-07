from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class Draft(Base, TimestampMixin):
    __tablename__ = "drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="drafts")
    sections = relationship("DraftSection", back_populates="draft", cascade="all, delete-orphan")


class DraftSection(Base, TimestampMixin):
    __tablename__ = "draft_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False)

    heading: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_with_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    source_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    draft = relationship("Draft", back_populates="sections")
    citations = relationship("DraftCitation", back_populates="section", cascade="all, delete-orphan")


class DraftCitation(Base, TimestampMixin):
    __tablename__ = "draft_citations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_section_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("draft_sections.id", ondelete="CASCADE"), nullable=False)
    reference_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("reference_items.id", ondelete="SET NULL"), nullable=True)
    paper_citation_span_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_citation_spans.id", ondelete="SET NULL"), nullable=True)

    marker: Mapped[str] = mapped_column(String(32), nullable=False)
    quoted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)

    section = relationship("DraftSection", back_populates="citations")


class EvidenceTable(Base, TimestampMixin):
    __tablename__ = "evidence_tables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    table_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    generated_from: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="evidence_tables")


Index("idx_drafts_project", Draft.project_id)
Index("idx_draft_sections_draft", DraftSection.draft_id)
Index("idx_evidence_tables_project", EvidenceTable.project_id)
