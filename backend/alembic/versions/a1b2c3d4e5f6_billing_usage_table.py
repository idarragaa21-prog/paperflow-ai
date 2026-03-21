"""billing: replace JSON file with usage_events table

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-03-21 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "a1b2c3d4e5f6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_usage_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_id", UUID(as_uuid=True), nullable=True),
        sa.Column("preset", sa.String(64), nullable=False, server_default="default"),
        sa.Column("models_used", JSONB, nullable=True),
        sa.Column("tokens_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("duration_sec", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_billing_user_created", "billing_usage_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_billing_user_created", table_name="billing_usage_events")
    op.drop_table("billing_usage_events")
