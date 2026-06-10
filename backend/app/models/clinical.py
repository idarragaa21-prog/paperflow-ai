from __future__ import annotations

import sqlalchemy as sa

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class ClinicalConsult(Base, TimestampMixin):
    __tablename__ = "clinical_consults"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), server_default="standard", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="completed", nullable=False)
    pico_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    answer_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uncertainty_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    used_project_library: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), nullable=False)
    used_pubmed: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sources = relationship("ClinicalConsultSource", back_populates="consult", cascade="all, delete-orphan")
    claims = relationship("ClinicalConsultClaim", back_populates="consult", cascade="all, delete-orphan")


class ClinicalConsultSource(Base, TimestampMixin):
    __tablename__ = "clinical_consult_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consult_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_consults.id", ondelete="CASCADE"), nullable=False)

    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    paper_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    reference_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("reference_items.id", ondelete="SET NULL"), nullable=True)

    pmid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    rank: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    relevance: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    consult = relationship("ClinicalConsult", back_populates="sources")


class ClinicalConsultClaim(Base, TimestampMixin):
    __tablename__ = "clinical_consult_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consult_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_consults.id", ondelete="CASCADE"), nullable=False)

    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    support_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uncertainty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    source_ids_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    consult = relationship("ClinicalConsult", back_populates="claims")


Index("idx_clinical_consults_user", ClinicalConsult.user_id)
Index("idx_clinical_consults_project", ClinicalConsult.project_id)
Index("idx_clinical_consult_sources_consult", ClinicalConsultSource.consult_id)
Index("idx_clinical_consult_claims_consult", ClinicalConsultClaim.consult_id)
