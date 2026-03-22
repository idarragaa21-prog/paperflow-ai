from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BillingUsageEvent(Base):
    """One row per Clinical PRO generation (or other billable action)."""

    __tablename__ = "billing_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    sheet_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True, native_uuid=True), nullable=True)
    preset: Mapped[str] = mapped_column(String(64), nullable=False, server_default="default")
    models_used: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default="0")
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
