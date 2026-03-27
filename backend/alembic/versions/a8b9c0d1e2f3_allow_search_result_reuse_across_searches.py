"""allow search result reuse across searches

Revision ID: a8b9c0d1e2f3
Revises: f0a1b2c3d4e5
Create Date: 2026-03-10 10:15:00.000000
"""

from alembic import op


revision = "a8b9c0d1e2f3"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_search_results_pmid_notnull;")
    op.execute("DROP INDEX IF EXISTS uq_search_results_doi_notnull;")


def downgrade() -> None:
    op.execute("CREATE UNIQUE INDEX uq_search_results_pmid_notnull ON search_results(pmid) WHERE pmid IS NOT NULL;")
    op.execute("CREATE UNIQUE INDEX uq_search_results_doi_notnull ON search_results(doi) WHERE doi IS NOT NULL;")
