from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Table, Column, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


presentation_papers = Table(
    "presentation_papers",
    Base.metadata,
    Column("presentation_id", UUID(as_uuid=True), ForeignKey("presentations.id", ondelete="CASCADE"), primary_key=True),
    Column("paper_id", UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
)


class Presentation(Base, TimestampMixin):
    __tablename__ = "presentations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audience: Mapped[str | None] = mapped_column(String(255), nullable=True)

    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    outline: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    references_used: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="presentations")
    papers = relationship("Paper", secondary=presentation_papers)


Index("idx_presentations_project", Presentation.project_id)
