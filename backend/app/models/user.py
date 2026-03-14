from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    invite_token: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    invite_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    highlights = relationship("PaperHighlight", back_populates="user", cascade="all, delete-orphan")
    screening_decisions = relationship("ScreeningDecision", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("ProjectComment", back_populates="user", cascade="all, delete-orphan")
    peer_review_actions = relationship("PeerReviewAction", back_populates="user", cascade="all, delete-orphan")
