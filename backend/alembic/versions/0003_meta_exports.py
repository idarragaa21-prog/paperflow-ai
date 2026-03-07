"""meta exports

Revision ID: 0003_meta_exports
Revises: 0002_meta_extractor
Create Date: 2026-02-08

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0003_meta_exports"
down_revision = "0002_meta_extractor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_meta_exports_project", "meta_exports", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_meta_exports_project", table_name="meta_exports")
    op.drop_table("meta_exports")
