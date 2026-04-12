"""paperflow vnext scope reset

Revision ID: b3d4e5f6a7b8
Revises: 7c4e9a9d1b2f
Create Date: 2026-04-11 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b3d4e5f6a7b8"
down_revision = "7c4e9a9d1b2f"
branch_labels = None
depends_on = None


def _drop_legacy_tables() -> None:
    # Hard scope cut: no backward compatibility for removed domains.
    op.execute(sa.text("DROP TABLE IF EXISTS presentation_papers CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS presentations CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS book_indexes CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS billing_usage_events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS clinical_sheets CASCADE"))


def upgrade() -> None:
    _drop_legacy_tables()

    op.create_table(
        "matrix_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("schema_version", sa.String(length=64), nullable=False, server_default="matrix.v1"),
        sa.Column("source_signature", sa.String(length=128), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_matrix_versions_project", "matrix_versions", ["project_id"], unique=False)
    op.create_index("idx_matrix_versions_project_current", "matrix_versions", ["project_id", "is_current"], unique=False)

    op.create_table(
        "matrix_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matrix_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extracted_study_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("row_key", sa.String(length=255), nullable=False),
        sa.Column("row_kind", sa.String(length=32), nullable=False, server_default="effect"),
        sa.Column("outcome_key", sa.String(length=255), nullable=True),
        sa.Column("effect_measure", sa.String(length=64), nullable=True),
        sa.Column("sort_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["matrix_version_id"], ["matrix_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["extracted_study_id"], ["extracted_studies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_matrix_rows_version", "matrix_rows", ["matrix_version_id"], unique=False)
    op.create_index("idx_matrix_rows_project", "matrix_rows", ["project_id"], unique=False)
    op.create_index("idx_matrix_rows_study", "matrix_rows", ["extracted_study_id"], unique=False)

    op.create_table(
        "matrix_provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matrix_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("source_locator", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["matrix_row_id"], ["matrix_rows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_matrix_provenance_row", "matrix_provenance", ["matrix_row_id"], unique=False)

    op.create_table(
        "matrix_validation_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matrix_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matrix_row_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="warning"),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["matrix_version_id"], ["matrix_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matrix_row_id"], ["matrix_rows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_matrix_validation_version", "matrix_validation_issues", ["matrix_version_id"], unique=False)
    op.create_index("idx_matrix_validation_row", "matrix_validation_issues", ["matrix_row_id"], unique=False)

    op.create_table(
        "derived_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matrix_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("preset", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("column_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("build_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_signature", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matrix_version_id"], ["matrix_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_derived_datasets_project", "derived_datasets", ["project_id"], unique=False)
    op.create_index("idx_derived_datasets_matrix", "derived_datasets", ["matrix_version_id"], unique=False)

    op.create_table(
        "meta_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matrix_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("derived_dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("preset", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("input_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("runtime_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("engine", sa.String(length=32), nullable=False, server_default="r-engine"),
        sa.Column("engine_version", sa.String(length=64), nullable=True),
        sa.Column("script_path", sa.Text(), nullable=True),
        sa.Column("session_info_path", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matrix_version_id"], ["matrix_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["derived_dataset_id"], ["derived_datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_meta_runs_project", "meta_runs", ["project_id"], unique=False)
    op.create_index("idx_meta_runs_matrix", "meta_runs", ["matrix_version_id"], unique=False)
    op.create_index("idx_meta_runs_dataset", "meta_runs", ["derived_dataset_id"], unique=False)

    op.create_table(
        "meta_run_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meta_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["meta_run_id"], ["meta_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_meta_run_artifacts_run", "meta_run_artifacts", ["meta_run_id"], unique=False)

    op.create_table(
        "clinical_consults",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("pico_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("input_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("answer_markdown", sa.Text(), nullable=True),
        sa.Column("answer_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("uncertainty_text", sa.Text(), nullable=True),
        sa.Column("limitations_text", sa.Text(), nullable=True),
        sa.Column("used_project_library", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("used_pubmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_clinical_consults_user", "clinical_consults", ["user_id"], unique=False)
    op.create_index("idx_clinical_consults_project", "clinical_consults", ["project_id"], unique=False)

    op.create_table(
        "clinical_consult_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consult_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pmid", sa.String(length=64), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("locator_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["consult_id"], ["clinical_consults.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reference_item_id"], ["reference_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_clinical_consult_sources_consult", "clinical_consult_sources", ["consult_id"], unique=False)

    op.create_table(
        "clinical_consult_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consult_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("support_level", sa.String(length=32), nullable=True),
        sa.Column("uncertainty", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["consult_id"], ["clinical_consults.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_clinical_consult_claims_consult", "clinical_consult_claims", ["consult_id"], unique=False)

    op.create_table(
        "writing_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False, server_default="narrative"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_writing_documents_project", "writing_documents", ["project_id"], unique=False)
    op.create_index("idx_writing_documents_user", "writing_documents", ["user_id"], unique=False)

    op.create_table(
        "writing_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_key", sa.String(length=64), nullable=False),
        sa.Column("heading", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("generated_with_model", sa.String(length=128), nullable=True),
        sa.Column("citations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["writing_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_writing_sections_document", "writing_sections", ["document_id"], unique=False)

    op.create_table(
        "writing_claim_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("citation_marker", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_locator", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["writing_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["writing_sections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_writing_claim_links_document", "writing_claim_links", ["document_id"], unique=False)
    op.create_index("idx_writing_claim_links_section", "writing_claim_links", ["section_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_writing_claim_links_section", table_name="writing_claim_links")
    op.drop_index("idx_writing_claim_links_document", table_name="writing_claim_links")
    op.drop_table("writing_claim_links")

    op.drop_index("idx_writing_sections_document", table_name="writing_sections")
    op.drop_table("writing_sections")

    op.drop_index("idx_writing_documents_user", table_name="writing_documents")
    op.drop_index("idx_writing_documents_project", table_name="writing_documents")
    op.drop_table("writing_documents")

    op.drop_index("idx_clinical_consult_claims_consult", table_name="clinical_consult_claims")
    op.drop_table("clinical_consult_claims")

    op.drop_index("idx_clinical_consult_sources_consult", table_name="clinical_consult_sources")
    op.drop_table("clinical_consult_sources")

    op.drop_index("idx_clinical_consults_project", table_name="clinical_consults")
    op.drop_index("idx_clinical_consults_user", table_name="clinical_consults")
    op.drop_table("clinical_consults")

    op.drop_index("idx_meta_run_artifacts_run", table_name="meta_run_artifacts")
    op.drop_table("meta_run_artifacts")

    op.drop_index("idx_meta_runs_dataset", table_name="meta_runs")
    op.drop_index("idx_meta_runs_matrix", table_name="meta_runs")
    op.drop_index("idx_meta_runs_project", table_name="meta_runs")
    op.drop_table("meta_runs")

    op.drop_index("idx_derived_datasets_matrix", table_name="derived_datasets")
    op.drop_index("idx_derived_datasets_project", table_name="derived_datasets")
    op.drop_table("derived_datasets")

    op.drop_index("idx_matrix_validation_row", table_name="matrix_validation_issues")
    op.drop_index("idx_matrix_validation_version", table_name="matrix_validation_issues")
    op.drop_table("matrix_validation_issues")

    op.drop_index("idx_matrix_provenance_row", table_name="matrix_provenance")
    op.drop_table("matrix_provenance")

    op.drop_index("idx_matrix_rows_study", table_name="matrix_rows")
    op.drop_index("idx_matrix_rows_project", table_name="matrix_rows")
    op.drop_index("idx_matrix_rows_version", table_name="matrix_rows")
    op.drop_table("matrix_rows")

    op.drop_index("idx_matrix_versions_project_current", table_name="matrix_versions")
    op.drop_index("idx_matrix_versions_project", table_name="matrix_versions")
    op.drop_table("matrix_versions")
