from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy import JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), server_default="manual", nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project = relationship("Project", back_populates="datasets")
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="dataset", cascade="all, delete-orphan")


class DatasetColumn(Base, TimestampMixin):
    __tablename__ = "dataset_columns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    dataset = relationship("Dataset", back_populates="columns")


class AnalysisRun(Base, TimestampMixin):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True, native_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="queued", nullable=False)
    input_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    runtime_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    engine_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    project = relationship("Project", back_populates="analysis_runs")
    dataset = relationship("Dataset", back_populates="analysis_runs")
    artifacts = relationship("AnalysisArtifact", back_populates="analysis_run", cascade="all, delete-orphan")
    figures = relationship("FigureArtifact", back_populates="analysis_run", cascade="all, delete-orphan")


class AnalysisArtifact(Base, TimestampMixin):
    __tablename__ = "analysis_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)

    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analysis_run = relationship("AnalysisRun", back_populates="artifacts")


class FigureArtifact(Base, TimestampMixin):
    __tablename__ = "figure_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analysis_run = relationship("AnalysisRun", back_populates="figures")


Index("idx_datasets_project", Dataset.project_id)
Index("idx_dataset_columns_dataset", DatasetColumn.dataset_id)
Index("idx_analysis_runs_project", AnalysisRun.project_id)
Index("idx_analysis_runs_dataset", AnalysisRun.dataset_id)
Index("idx_analysis_artifacts_run", AnalysisArtifact.analysis_run_id)
