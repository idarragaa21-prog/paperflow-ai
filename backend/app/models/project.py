from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    runtime_mode: Mapped[str] = mapped_column(String(32), server_default="local_only", nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    user = relationship("User", back_populates="projects")
    searches = relationship("Search", back_populates="project", cascade="all, delete-orphan")
    papers = relationship("Paper", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="project", cascade="all, delete-orphan")
    presentations = relationship("Presentation", back_populates="project", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="project", cascade="all, delete-orphan")
    extraction_records = relationship("ExtractionRecord", back_populates="project", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="project", cascade="all, delete-orphan")
    evidence_tables = relationship("EvidenceTable", back_populates="project", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="project", cascade="all, delete-orphan")
    screening_batches = relationship("ScreeningBatch", back_populates="project", cascade="all, delete-orphan")
    review_flows = relationship("ReviewFlow", back_populates="project", cascade="all, delete-orphan")
    eligibility_reasons = relationship("EligibilityReason", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("ProjectComment", back_populates="project", cascade="all, delete-orphan")
    peer_review_actions = relationship("PeerReviewAction", back_populates="project", cascade="all, delete-orphan")


Index("idx_projects_user", Project.user_id)
