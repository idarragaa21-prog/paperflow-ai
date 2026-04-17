"""user: add affiliation, ORCID, signature, language and preferences

Revision ID: d6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-16 00:00:00.000000

Adds optional personalization fields for the local single-user workflow:
- affiliation (institution / department) used in cover letters and DOCX exports
- orcid for reference style display
- signature_md for letter / cover letter sign-off blocks
- language for default UI locale (es/en/pt)
- preferences JSONB for forward-compatible UI preferences
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("affiliation", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("orcid", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("signature_md", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("language", sa.String(length=8), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "preferences")
    op.drop_column("users", "language")
    op.drop_column("users", "signature_md")
    op.drop_column("users", "orcid")
    op.drop_column("users", "affiliation")
