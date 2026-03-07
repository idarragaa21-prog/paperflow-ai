"""clinical sheets and book index

Revision ID: 6266b3fe61eb
Revises: 8c9d4455200d
Create Date: 2026-02-09 10:15:12.746396

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '6266b3fe61eb'
down_revision = '8c9d4455200d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinical_sheets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("input_params", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("references_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("sources_used", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("llm_model", sa.String(length=128), nullable=True),
        sa.Column("llm_usage", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_clinical_sheets_user", "clinical_sheets", ["user_id"])
    op.create_index("idx_clinical_sheets_project", "clinical_sheets", ["project_id"])

    op.create_table(
        "book_indexes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column("chapters", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_book_indexes_user", "book_indexes", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_book_indexes_user", table_name="book_indexes")
    op.drop_table("book_indexes")

    op.drop_index("idx_clinical_sheets_project", table_name="clinical_sheets")
    op.drop_index("idx_clinical_sheets_user", table_name="clinical_sheets")
    op.drop_table("clinical_sheets")
