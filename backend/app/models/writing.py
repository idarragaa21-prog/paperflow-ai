from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class WritingDocument(Base, TimestampMixin):
    __tablename__ = "writing_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(64), server_default="narrative", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="writing_documents")
    sections = relationship("WritingSection", back_populates="document", cascade="all, delete-orphan")
    claim_links = relationship("WritingClaimLink", back_populates="document", cascade="all, delete-orphan")


class WritingSection(Base, TimestampMixin):
    __tablename__ = "writing_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("writing_documents.id", ondelete="CASCADE"), nullable=False)

    section_key: Mapped[str] = mapped_column(String(64), nullable=False)
    heading: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False)

    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_with_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    citations_json: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document = relationship("WritingDocument", back_populates="sections")
    claim_links = relationship("WritingClaimLink", back_populates="section", cascade="all, delete-orphan")


class WritingClaimLink(Base, TimestampMixin):
    __tablename__ = "writing_claim_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("writing_documents.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("writing_sections.id", ondelete="SET NULL"), nullable=True)

    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    citation_marker: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    source_locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document = relationship("WritingDocument", back_populates="claim_links")
    section = relationship("WritingSection", back_populates="claim_links")


Index("idx_writing_documents_project", WritingDocument.project_id)
Index("idx_writing_documents_user", WritingDocument.user_id)
Index("idx_writing_sections_document", WritingSection.document_id)
Index("idx_writing_claim_links_document", WritingClaimLink.document_id)
Index("idx_writing_claim_links_section", WritingClaimLink.section_id)
