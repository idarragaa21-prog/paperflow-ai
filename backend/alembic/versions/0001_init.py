"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-02-08

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Utility function for updated_at triggers
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # projects
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("clinical_area", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index("idx_projects_user", "projects", ["user_id"], unique=False)

    op.execute(
        """
        CREATE TRIGGER update_projects_updated_at
        BEFORE UPDATE ON projects
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # searches
    op.create_table(
        "searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_searches_project", "searches", ["project_id"], unique=False)

    # search_results
    op.create_table(
        "search_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("search_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pmid", sa.String(length=64), nullable=True),
        sa.Column("pmcid", sa.String(length=64), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("journal", sa.String(length=255), nullable=True),
        sa.Column("pub_year", sa.Integer(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("is_open_access", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("oa_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_search_results_pmid", "search_results", ["pmid"], unique=False)
    op.create_index("idx_search_results_doi", "search_results", ["doi"], unique=False)

    # Handle NULL-safe uniqueness using partial indexes
    op.execute("CREATE UNIQUE INDEX uq_search_results_pmid_notnull ON search_results(pmid) WHERE pmid IS NOT NULL;")
    op.execute("CREATE UNIQUE INDEX uq_search_results_doi_notnull ON search_results(doi) WHERE doi IS NOT NULL;")

    # papers
    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("search_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("search_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("pmid", sa.String(length=64), nullable=True),
        sa.Column("pmcid", sa.String(length=64), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size_kb", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_processed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("full_text_extracted", sa.Text(), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("project_id", "content_hash", name="uq_papers_project_hash"),
    )
    op.create_index("idx_papers_project", "papers", ["project_id"], unique=False)
    op.create_index("idx_papers_hash", "papers", ["content_hash"], unique=False)

    # notes
    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("note_type", sa.String(length=100), nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("llm_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        """
        CREATE TRIGGER update_notes_updated_at
        BEFORE UPDATE ON notes
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # presentations
    op.create_table(
        "presentations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("audience", sa.String(length=255), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("outline", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("references_used", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("llm_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # presentation_papers (m2m)
    op.create_table(
        "presentation_papers",
        sa.Column("presentation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("presentations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    )

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_jobs_user_status", "jobs", ["user_id", "status"], unique=False)

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_audit_logs_user_time", "audit_logs", ["user_id", sa.text("created_at DESC")], unique=False)


def downgrade() -> None:
    op.drop_index("idx_audit_logs_user_time", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("idx_jobs_user_status", table_name="jobs")
    op.drop_table("jobs")

    op.drop_table("presentation_papers")
    op.drop_table("presentations")

    op.execute("DROP TRIGGER IF EXISTS update_notes_updated_at ON notes;")
    op.drop_table("notes")

    op.drop_index("idx_papers_hash", table_name="papers")
    op.drop_index("idx_papers_project", table_name="papers")
    op.drop_table("papers")

    op.execute("DROP INDEX IF EXISTS uq_search_results_pmid_notnull;")
    op.execute("DROP INDEX IF EXISTS uq_search_results_doi_notnull;")
    op.drop_index("idx_search_results_doi", table_name="search_results")
    op.drop_index("idx_search_results_pmid", table_name="search_results")
    op.drop_table("search_results")

    op.drop_index("idx_searches_project", table_name="searches")
    op.drop_table("searches")

    op.execute("DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;")
    op.drop_index("idx_projects_user", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column;")
