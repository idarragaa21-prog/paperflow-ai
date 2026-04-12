"""drop legacy drafts/analysis/screening tables after vNext cut

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-12 18:30:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


LEGACY_TABLES = [
    # Drafts / writing legacy
    "draft_citations",
    "draft_sections",
    "drafts",
    # Legacy analysis stack
    "figure_artifacts",
    "analysis_artifacts",
    "analysis_runs",
    "dataset_columns",
    "datasets",
    "evidence_tables",
    # Legacy screening stack
    "screening_decisions",
    "eligibility_reasons",
    "screening_batches",
]


def upgrade() -> None:
    for table_name in LEGACY_TABLES:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))


def downgrade() -> None:
    # Hard scope cut: removed domains are intentionally non-recoverable via downgrade.
    pass
