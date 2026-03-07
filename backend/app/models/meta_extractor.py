from __future__ import annotations

from datetime import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetaExtractionBatch(Base):
    __tablename__ = "meta_extraction_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), server_default="created", nullable=False)  # created|processing|completed|failed

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("idx_meta_batch_project", MetaExtractionBatch.project_id)


class MetaExtractionItem(Base):
    __tablename__ = "meta_extraction_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta_extraction_batches.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(32), server_default="queued", nullable=False)  # queued|started|completed|failed
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("idx_meta_item_batch", MetaExtractionItem.batch_id)


class ExtractedStudy(Base):
    __tablename__ = "extracted_studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meta_extraction_batches.id", ondelete="SET NULL"), nullable=True)

    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    study_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(sa.Float(), server_default="0.0", nullable=False)  # type: ignore[name-defined]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("idx_extracted_study_project", ExtractedStudy.project_id)
Index("idx_extracted_study_paper", ExtractedStudy.paper_id)


class ExtractedEffectSize(Base):
    __tablename__ = "extracted_effect_sizes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extracted_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_studies.id", ondelete="CASCADE"), nullable=False)

    outcome_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timepoint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    arm_intervention: Mapped[str] = mapped_column(String(255), nullable=False)
    arm_control: Mapped[str] = mapped_column(String(255), nullable=False)

    effect_measure: Mapped[str] = mapped_column(String(32), server_default="OR", nullable=False)

    a_events: Mapped[int | None] = mapped_column(Integer, nullable=True)
    b_non_events: Mapped[int | None] = mapped_column(Integer, nullable=True)
    c_events: Mapped[int | None] = mapped_column(Integer, nullable=True)
    d_non_events: Mapped[int | None] = mapped_column(Integer, nullable=True)

    or_value: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]
    log_or: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]
    se_log_or: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]
    ci_lower_95: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]
    ci_upper_95: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]

    adjusted_or: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]
    adjusted_rr: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]
    adjusted_hr: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)  # type: ignore[name-defined]

    adjustment_variables: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_adjusted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    raw_extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), server_default="text", nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    confidence: Mapped[float] = mapped_column(sa.Float(), server_default="0.0", nullable=False)  # type: ignore[name-defined]
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    manually_edited: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index("idx_effectsizes_study", ExtractedEffectSize.extracted_study_id)


class ExtractedRiskOfBias(Base):
    __tablename__ = "extracted_risk_of_bias"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extracted_study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_studies.id", ondelete="CASCADE"), nullable=False)

    tool: Mapped[str] = mapped_column(String(32), server_default="ROB2", nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    judgement: Mapped[str] = mapped_column(String(32), server_default="unclear", nullable=False)
    support_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    manually_edited: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    auto_generated: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)


Index("idx_rob_study", ExtractedRiskOfBias.extracted_study_id)
