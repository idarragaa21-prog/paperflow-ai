from __future__ import annotations

import sqlalchemy as sa

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class ExtractionTemplate(Base, TimestampMixin):
    __tablename__ = "extraction_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discipline: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    records = relationship("ExtractionRecord", back_populates="template")


class ExtractionRecord(Base, TimestampMixin):
    __tablename__ = "extraction_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extraction_templates.id", ondelete="RESTRICT"), nullable=False)

    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="extraction_records")
    paper = relationship("Paper", back_populates="extraction_records")
    template = relationship("ExtractionTemplate", back_populates="records")
    field_values = relationship("ExtractionFieldValue", back_populates="record", cascade="all, delete-orphan")


class ExtractionFieldValue(Base, TimestampMixin):
    __tablename__ = "extraction_field_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extraction_records.id", ondelete="CASCADE"), nullable=False)

    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    manually_edited: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)

    record = relationship("ExtractionRecord", back_populates="field_values")


Index("idx_extraction_records_project", ExtractionRecord.project_id)
Index("idx_extraction_records_paper", ExtractionRecord.paper_id)
Index("idx_extraction_field_values_record", ExtractionFieldValue.record_id)
