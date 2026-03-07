"""paperflow research workbench

Revision ID: c7f8a9b0d1e2
Revises: b1d2c3e4f5a6
Create Date: 2026-03-06

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c7f8a9b0d1e2"
down_revision = "b1d2c3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("runtime_mode", sa.String(length=32), server_default="local_only", nullable=False))

    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("task_type", sa.String(length=32), server_default="chat", nullable=False),
        sa.Column("runtime_mode", sa.String(length=32), server_default="local_only", nullable=False),
        sa.Column("grounded", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_chat_sessions_project", "chat_sessions", ["project_id"], unique=False)
    op.create_index("idx_chat_sessions_paper", "chat_sessions", ["paper_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=16), server_default="resumen", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("grounded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_chat_messages_session", "chat_messages", ["session_id"], unique=False)

    op.create_table(
        "retrieved_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("locator", postgresql.JSONB(), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "answer_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("locator", postgresql.JSONB(), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "paper_highlights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("color", sa.String(length=32), server_default="yellow", nullable=False),
        sa.Column("note_text", sa.Text(), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=True),
        sa.Column("locator", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_paper_highlights_paper", "paper_highlights", ["paper_id"], unique=False)

    op.create_table(
        "extraction_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discipline", sa.String(length=128), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("schema_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "extraction_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extraction_templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_extraction_records_project", "extraction_records", ["project_id"], unique=False)
    op.create_index("idx_extraction_records_paper", "extraction_records", ["paper_id"], unique=False)

    op.create_table(
        "extraction_field_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extraction_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("auto_value_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_locator", postgresql.JSONB(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("manually_edited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_extraction_field_values_record", "extraction_field_values", ["record_id"], unique=False)

    op.create_table(
        "drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_drafts_project", "drafts", ["project_id"], unique=False)

    op.create_table(
        "draft_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("heading", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generated_with_model", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("source_summary", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_draft_sections_draft", "draft_sections", ["draft_id"], unique=False)

    op.create_table(
        "draft_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("draft_section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("draft_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reference_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("paper_citation_span_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_citation_spans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("marker", sa.String(length=32), nullable=False),
        sa.Column("quoted_text", sa.Text(), nullable=True),
        sa.Column("locator", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "evidence_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("table_json", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("generated_from", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_evidence_tables_project", "evidence_tables", ["project_id"], unique=False)

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("column_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("schema_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_datasets_project", "datasets", ["project_id"], unique=False)

    op.create_table(
        "dataset_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_nullable", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_dataset_columns_dataset", "dataset_columns", ["dataset_id"], unique=False)

    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("analysis_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("input_params", postgresql.JSONB(), nullable=True),
        sa.Column("runtime_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("script_text", sa.Text(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(), nullable=True),
        sa.Column("engine_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_analysis_runs_project", "analysis_runs", ["project_id"], unique=False)
    op.create_index("idx_analysis_runs_dataset", "analysis_runs", ["dataset_id"], unique=False)

    op.create_table(
        "analysis_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_analysis_artifacts_run", "analysis_artifacts", ["analysis_run_id"], unique=False)

    op.create_table(
        "figure_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "screening_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("stage", sa.String(length=32), server_default="title_abstract", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_screening_batches_project", "screening_batches", ["project_id"], unique=False)

    op.create_table(
        "eligibility_reasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_eligibility_reasons_project", "eligibility_reasons", ["project_id"], unique=False)

    op.create_table(
        "screening_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("screening_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eligibility_reasons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", sa.String(length=32), server_default="title_abstract", nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_screening_decisions_batch", "screening_decisions", ["batch_id"], unique=False)

    op.create_table(
        "review_flows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("config_json", postgresql.JSONB(), nullable=True),
        sa.Column("prisma_counts_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_review_flows_project", "review_flows", ["project_id"], unique=False)

    op.create_table(
        "project_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "peer_review_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("peer_review_actions")
    op.drop_table("project_comments")

    op.drop_index("idx_review_flows_project", table_name="review_flows")
    op.drop_table("review_flows")

    op.drop_index("idx_screening_decisions_batch", table_name="screening_decisions")
    op.drop_table("screening_decisions")

    op.drop_index("idx_eligibility_reasons_project", table_name="eligibility_reasons")
    op.drop_table("eligibility_reasons")

    op.drop_index("idx_screening_batches_project", table_name="screening_batches")
    op.drop_table("screening_batches")

    op.drop_table("figure_artifacts")

    op.drop_index("idx_analysis_artifacts_run", table_name="analysis_artifacts")
    op.drop_table("analysis_artifacts")

    op.drop_index("idx_analysis_runs_dataset", table_name="analysis_runs")
    op.drop_index("idx_analysis_runs_project", table_name="analysis_runs")
    op.drop_table("analysis_runs")

    op.drop_index("idx_dataset_columns_dataset", table_name="dataset_columns")
    op.drop_table("dataset_columns")

    op.drop_index("idx_datasets_project", table_name="datasets")
    op.drop_table("datasets")

    op.drop_index("idx_evidence_tables_project", table_name="evidence_tables")
    op.drop_table("evidence_tables")

    op.drop_table("draft_citations")

    op.drop_index("idx_draft_sections_draft", table_name="draft_sections")
    op.drop_table("draft_sections")

    op.drop_index("idx_drafts_project", table_name="drafts")
    op.drop_table("drafts")

    op.drop_index("idx_extraction_field_values_record", table_name="extraction_field_values")
    op.drop_table("extraction_field_values")

    op.drop_index("idx_extraction_records_paper", table_name="extraction_records")
    op.drop_index("idx_extraction_records_project", table_name="extraction_records")
    op.drop_table("extraction_records")

    op.drop_table("extraction_templates")

    op.drop_index("idx_paper_highlights_paper", table_name="paper_highlights")
    op.drop_table("paper_highlights")

    op.drop_table("answer_citations")
    op.drop_table("retrieved_chunks")

    op.drop_index("idx_chat_messages_session", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("idx_chat_sessions_paper", table_name="chat_sessions")
    op.drop_index("idx_chat_sessions_project", table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_column("projects", "runtime_mode")
