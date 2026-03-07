"""drop private clinical sources

Revision ID: 1c07329430eb
Revises: d4c7f977358c
Create Date: 2026-02-09 12:58:32.528996

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1c07329430eb'
down_revision = 'd4c7f977358c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_private_sources_type", table_name="private_clinical_sources")
    op.drop_index("idx_private_sources_project", table_name="private_clinical_sources")
    op.drop_index("idx_private_sources_user", table_name="private_clinical_sources")
    op.drop_table("private_clinical_sources")


def downgrade() -> None:
    # Recreate table (best-effort) to allow downgrade.
    from sqlalchemy.dialects import postgresql

    op.create_table(
        "private_clinical_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("permissions", postgresql.JSONB(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("index_status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("index_error", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("idx_private_sources_user", "private_clinical_sources", ["user_id"])
    op.create_index("idx_private_sources_project", "private_clinical_sources", ["project_id"])
    op.create_index("idx_private_sources_type", "private_clinical_sources", ["source_type"])
