"""paperflow document foundation

Revision ID: b1d2c3e4f5a6
Revises: 9ebe2c19554a
Create Date: 2026-03-06

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b1d2c3e4f5a6"
down_revision = "9ebe2c19554a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("papers", sa.Column("journal", sa.String(length=255), nullable=True))
    op.add_column("papers", sa.Column("publication_year", sa.Integer(), nullable=True))
    op.add_column("papers", sa.Column("language", sa.String(length=32), nullable=True))
    op.add_column("papers", sa.Column("abstract_text", sa.Text(), nullable=True))
    op.add_column("papers", sa.Column("source_provider", sa.String(length=64), nullable=True))
    op.add_column("papers", sa.Column("source_type", sa.String(length=64), nullable=True))
    op.add_column("papers", sa.Column("is_open_access", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("papers", sa.Column("oa_url", sa.Text(), nullable=True))
    op.add_column("papers", sa.Column("favorite", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("papers", sa.Column("tags", postgresql.JSONB(), nullable=True))
    op.add_column("papers", sa.Column("processing_status", sa.String(length=32), server_default="uploaded", nullable=False))
    op.add_column("papers", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("papers", sa.Column("processing_warnings", postgresql.JSONB(), nullable=True))

    op.add_column("search_results", sa.Column("source", sa.String(length=64), nullable=True))
    op.add_column("search_results", sa.Column("language", sa.String(length=32), nullable=True))

    op.create_table(
        "paper_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), server_default="application/pdf", nullable=False),
        sa.Column("size_kb", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_paper_files_paper", "paper_files", ["paper_id"], unique=False)

    op.create_table(
        "paper_parse_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("parser_name", sa.String(length=64), server_default="paperflow_pdf_v1", nullable=False),
        sa.Column("parser_version", sa.String(length=32), server_default="1", nullable=False),
        sa.Column("used_ocr", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("pages_count", sa.Integer(), nullable=True),
        sa.Column("chars_extracted", sa.Integer(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_parse_runs_paper", "paper_parse_runs", ["paper_id"], unique=False)

    op.create_table(
        "paper_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parse_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_parse_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("locator", postgresql.JSONB(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_paper_chunks_paper_page", "paper_chunks", ["paper_id", "page_number"], unique=False)

    op.create_table(
        "paper_citation_spans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parse_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_parse_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("locator", postgresql.JSONB(), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_paper_citations_paper_page", "paper_citation_spans", ["paper_id", "page_number"], unique=False)

    op.create_table(
        "reference_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_format", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("citation_key", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", postgresql.JSONB(), nullable=True),
        sa.Column("journal", sa.String(length=255), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("pmid", sa.String(length=64), nullable=True),
        sa.Column("pmcid", sa.String(length=64), nullable=True),
        sa.Column("abstract_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_reference_items_project", "reference_items", ["project_id"], unique=False)
    op.create_index("idx_reference_items_paper", "reference_items", ["paper_id"], unique=False)
    op.create_index("idx_reference_items_doi", "reference_items", ["doi"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_reference_items_doi", table_name="reference_items")
    op.drop_index("idx_reference_items_paper", table_name="reference_items")
    op.drop_index("idx_reference_items_project", table_name="reference_items")
    op.drop_table("reference_items")

    op.drop_index("idx_paper_citations_paper_page", table_name="paper_citation_spans")
    op.drop_table("paper_citation_spans")

    op.drop_index("idx_paper_chunks_paper_page", table_name="paper_chunks")
    op.drop_table("paper_chunks")

    op.drop_index("idx_parse_runs_paper", table_name="paper_parse_runs")
    op.drop_table("paper_parse_runs")

    op.drop_index("idx_paper_files_paper", table_name="paper_files")
    op.drop_table("paper_files")

    op.drop_column("search_results", "language")
    op.drop_column("search_results", "source")

    op.drop_column("papers", "processing_warnings")
    op.drop_column("papers", "processing_error")
    op.drop_column("papers", "processing_status")
    op.drop_column("papers", "tags")
    op.drop_column("papers", "favorite")
    op.drop_column("papers", "oa_url")
    op.drop_column("papers", "is_open_access")
    op.drop_column("papers", "source_type")
    op.drop_column("papers", "source_provider")
    op.drop_column("papers", "abstract_text")
    op.drop_column("papers", "language")
    op.drop_column("papers", "publication_year")
    op.drop_column("papers", "journal")
