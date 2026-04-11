from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class DerivedDataset(Base, TimestampMixin):
    __tablename__ = "derived_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    matrix_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matrix_versions.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    preset: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="ready", nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    schema_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    build_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)

    project = relationship("Project", back_populates="derived_datasets")
    meta_runs = relationship("MetaRun", back_populates="derived_dataset", cascade="all, delete-orphan")


class MetaRun(Base, TimestampMixin):
    __tablename__ = "meta_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    matrix_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("matrix_versions.id", ondelete="SET NULL"), nullable=True)
    derived_dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("derived_datasets.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    preset: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="queued", nullable=False)
    input_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    runtime_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    engine: Mapped[str] = mapped_column(String(32), server_default="r-engine", nullable=False)
    engine_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    script_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_info_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="meta_runs")
    derived_dataset = relationship("DerivedDataset", back_populates="meta_runs")
    artifacts = relationship("MetaRunArtifact", back_populates="meta_run", cascade="all, delete-orphan")


class MetaRunArtifact(Base, TimestampMixin):
    __tablename__ = "meta_run_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meta_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meta_runs.id", ondelete="CASCADE"), nullable=False)

    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    meta_run = relationship("MetaRun", back_populates="artifacts")


Index("idx_derived_datasets_project", DerivedDataset.project_id)
Index("idx_derived_datasets_matrix", DerivedDataset.matrix_version_id)
Index("idx_meta_runs_project", MetaRun.project_id)
Index("idx_meta_runs_dataset", MetaRun.derived_dataset_id)
Index("idx_meta_runs_matrix", MetaRun.matrix_version_id)
Index("idx_meta_run_artifacts_run", MetaRunArtifact.meta_run_id)
