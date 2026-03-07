from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClinicalSheet(Base):
    __tablename__ = "clinical_sheets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    input_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    # PRO structured output (validated JSON); keep markdown for export/human readability
    content_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    format_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    references_json: Mapped[list[dict] | dict | None] = mapped_column(JSONB, nullable=True)
    sources_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("idx_clinical_sheets_user", ClinicalSheet.user_id)
Index("idx_clinical_sheets_project", ClinicalSheet.project_id)
