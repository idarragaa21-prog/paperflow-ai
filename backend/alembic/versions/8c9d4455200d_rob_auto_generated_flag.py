"""rob auto_generated flag

Revision ID: 8c9d4455200d
Revises: 0003_meta_exports
Create Date: 2026-02-09 10:12:11.944220

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '8c9d4455200d'
down_revision = '0003_meta_exports'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extracted_risk_of_bias",
        sa.Column("auto_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("extracted_risk_of_bias", "auto_generated")
