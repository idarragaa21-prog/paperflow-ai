"""search_result: add relevance_score column

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2025-03-19 00:00:00.000000

Adds a nullable FLOAT column to search_results for storing the
relevance score computed at search time. Existing rows default to NULL,
which the ORDER BY … NULLS LAST clause handles gracefully.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "search_results",
        sa.Column("relevance_score", sa.Float(), nullable=True),
    )
    # Index for sorting history queries efficiently
    op.create_index(
        "idx_search_results_relevance",
        "search_results",
        ["search_id", "relevance_score"],
    )


def downgrade() -> None:
    op.drop_index("idx_search_results_relevance", table_name="search_results")
    op.drop_column("search_results", "relevance_score")
