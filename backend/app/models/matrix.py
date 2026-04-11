from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class MatrixVersion(Base, TimestampMixin):
    __tablename__ = "matrix_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    version_number: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="ready", nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), server_default="matrix.v1", nullable=False)
    source_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rows = relationship("MatrixRow", back_populates="matrix_version", cascade="all, delete-orphan")
    validation_issues = relationship("MatrixValidationIssue", back_populates="matrix_version", cascade="all, delete-orphan")
    project = relationship("Project", back_populates="matrix_versions")


class MatrixRow(Base, TimestampMixin):
    __tablename__ = "matrix_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matrix_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matrix_versions.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    extracted_study_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_studies.id", ondelete="SET NULL"), nullable=True)

    row_key: Mapped[str] = mapped_column(String(255), nullable=False)
    row_kind: Mapped[str] = mapped_column(String(32), server_default="effect", nullable=False)
    outcome_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effect_measure: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_index: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    data_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    matrix_version = relationship("MatrixVersion", back_populates="rows")
    provenance = relationship("MatrixProvenance", back_populates="matrix_row", cascade="all, delete-orphan")
    validation_issues = relationship("MatrixValidationIssue", back_populates="matrix_row")


class MatrixProvenance(Base, TimestampMixin):
    __tablename__ = "matrix_provenance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matrix_row_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matrix_rows.id", ondelete="CASCADE"), nullable=False)

    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    matrix_row = relationship("MatrixRow", back_populates="provenance")


class MatrixValidationIssue(Base, TimestampMixin):
    __tablename__ = "matrix_validation_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matrix_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matrix_versions.id", ondelete="CASCADE"), nullable=False)
    matrix_row_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("matrix_rows.id", ondelete="SET NULL"), nullable=True)

    severity: Mapped[str] = mapped_column(String(16), server_default="warning", nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    matrix_version = relationship("MatrixVersion", back_populates="validation_issues")
    matrix_row = relationship("MatrixRow", back_populates="validation_issues")


Index("idx_matrix_versions_project", MatrixVersion.project_id)
Index("idx_matrix_versions_project_current", MatrixVersion.project_id, MatrixVersion.is_current)
Index("idx_matrix_rows_version", MatrixRow.matrix_version_id)
Index("idx_matrix_rows_project", MatrixRow.project_id)
Index("idx_matrix_rows_study", MatrixRow.extracted_study_id)
Index("idx_matrix_provenance_row", MatrixProvenance.matrix_row_id)
Index("idx_matrix_validation_version", MatrixValidationIssue.matrix_version_id)
Index("idx_matrix_validation_row", MatrixValidationIssue.matrix_row_id)
