"""private clinical sources

Revision ID: d4c7f977358c
Revises: 6266b3fe61eb
Create Date: 2026-02-09 12:29:00.105968

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision = 'd4c7f977358c'
down_revision = '6266b3fe61eb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "private_clinical_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
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


def downgrade() -> None:
    op.drop_index("idx_private_sources_type", table_name="private_clinical_sources")
    op.drop_index("idx_private_sources_project", table_name="private_clinical_sources")
    op.drop_index("idx_private_sources_user", table_name="private_clinical_sources")
    op.drop_table("private_clinical_sources")
