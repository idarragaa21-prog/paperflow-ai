"""clinical pro structured output

Revision ID: 9ebe2c19554a
Revises: 1c07329430eb
Create Date: 2026-02-09 13:28:38.072678

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '9ebe2c19554a'
down_revision = '1c07329430eb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.add_column("clinical_sheets", sa.Column("content_json", postgresql.JSONB(), nullable=True))
    op.add_column("clinical_sheets", sa.Column("format_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("clinical_sheets", "format_version")
    op.drop_column("clinical_sheets", "content_json")
