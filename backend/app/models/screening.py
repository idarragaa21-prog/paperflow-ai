from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class ScreeningBatch(Base, TimestampMixin):
    __tablename__ = "screening_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), server_default="title_abstract", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="active", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="screening_batches")
    decisions = relationship("ScreeningDecision", back_populates="batch", cascade="all, delete-orphan")


class EligibilityReason(Base, TimestampMixin):
    __tablename__ = "eligibility_reasons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    project = relationship("Project", back_populates="eligibility_reasons")
    decisions = relationship("ScreeningDecision", back_populates="reason")


class ScreeningDecision(Base, TimestampMixin):
    __tablename__ = "screening_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screening_batches.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("eligibility_reasons.id", ondelete="SET NULL"), nullable=True)

    stage: Mapped[str] = mapped_column(String(32), server_default="title_abstract", nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    batch = relationship("ScreeningBatch", back_populates="decisions")
    reason = relationship("EligibilityReason", back_populates="decisions")
    user = relationship("User", back_populates="screening_decisions")


class ReviewFlow(Base, TimestampMixin):
    __tablename__ = "review_flows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    prisma_counts_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="review_flows")


class ProjectComment(Base, TimestampMixin):
    __tablename__ = "project_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    project = relationship("Project", back_populates="comments")
    user = relationship("User", back_populates="comments")


class PeerReviewAction(Base, TimestampMixin):
    __tablename__ = "peer_review_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="open", nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="peer_review_actions")
    user = relationship("User", back_populates="peer_review_actions")


Index("idx_screening_batches_project", ScreeningBatch.project_id)
Index("idx_screening_decisions_batch", ScreeningDecision.batch_id)
Index("idx_eligibility_reasons_project", EligibilityReason.project_id)
Index("idx_review_flows_project", ReviewFlow.project_id)
