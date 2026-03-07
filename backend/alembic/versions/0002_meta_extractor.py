"""meta extractor

Revision ID: 0002_meta_extractor
Revises: 0001_init
Create Date: 2026-02-08

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0002_meta_extractor"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_extraction_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'created'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_meta_batch_project", "meta_extraction_batches", ["project_id"], unique=False)

    op.create_table(
        "meta_extraction_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meta_extraction_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_meta_item_batch", "meta_extraction_items", ["batch_id"], unique=False)

    op.execute(
        """
        CREATE TRIGGER update_meta_extraction_items_updated_at
        BEFORE UPDATE ON meta_extraction_items
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.create_table(
        "extracted_studies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meta_extraction_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("study_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extraction_confidence", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("idx_extracted_study_project", "extracted_studies", ["project_id"], unique=False)
    op.create_index("idx_extracted_study_paper", "extracted_studies", ["paper_id"], unique=False)
    op.execute(
        "CREATE INDEX idx_extracted_study_current ON extracted_studies(paper_id, is_current) WHERE is_current = true;"
    )

    op.execute(
        """
        CREATE TRIGGER update_extracted_studies_updated_at
        BEFORE UPDATE ON extracted_studies
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.create_table(
        "extracted_effect_sizes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "extracted_study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extracted_studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome_name", sa.String(length=255), nullable=False),
        sa.Column("timepoint", sa.String(length=255), nullable=True),
        sa.Column("arm_intervention", sa.String(length=255), nullable=False),
        sa.Column("arm_control", sa.String(length=255), nullable=False),
        sa.Column("effect_measure", sa.String(length=32), server_default=sa.text("'OR'"), nullable=False),
        sa.Column("a_events", sa.Integer(), nullable=True),
        sa.Column("b_non_events", sa.Integer(), nullable=True),
        sa.Column("c_events", sa.Integer(), nullable=True),
        sa.Column("d_non_events", sa.Integer(), nullable=True),
        sa.Column("or_value", sa.Float(), nullable=True),
        sa.Column("log_or", sa.Float(), nullable=True),
        sa.Column("se_log_or", sa.Float(), nullable=True),
        sa.Column("ci_lower_95", sa.Float(), nullable=True),
        sa.Column("ci_upper_95", sa.Float(), nullable=True),
        sa.Column("adjusted_or", sa.Float(), nullable=True),
        sa.Column("adjusted_rr", sa.Float(), nullable=True),
        sa.Column("adjusted_hr", sa.Float(), nullable=True),
        sa.Column("adjustment_variables", sa.Text(), nullable=True),
        sa.Column("is_adjusted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("raw_extracted_value", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=32), server_default=sa.text("'text'"), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_locator", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("manually_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_effectsizes_study", "extracted_effect_sizes", ["extracted_study_id"], unique=False)

    op.create_table(
        "extracted_risk_of_bias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "extracted_study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extracted_studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool", sa.String(length=32), server_default=sa.text("'ROB2'"), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("judgement", sa.String(length=32), server_default=sa.text("'unclear'"), nullable=False),
        sa.Column("support_text", sa.Text(), nullable=True),
        sa.Column("manually_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_rob_study", "extracted_risk_of_bias", ["extracted_study_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_rob_study", table_name="extracted_risk_of_bias")
    op.drop_table("extracted_risk_of_bias")

    op.drop_index("idx_effectsizes_study", table_name="extracted_effect_sizes")
    op.drop_table("extracted_effect_sizes")

    op.execute("DROP TRIGGER IF EXISTS update_extracted_studies_updated_at ON extracted_studies;")
    op.drop_index("idx_extracted_study_current")
    op.drop_index("idx_extracted_study_paper", table_name="extracted_studies")
    op.drop_index("idx_extracted_study_project", table_name="extracted_studies")
    op.drop_table("extracted_studies")

    op.execute("DROP TRIGGER IF EXISTS update_meta_extraction_items_updated_at ON meta_extraction_items;")
    op.drop_index("idx_meta_item_batch", table_name="meta_extraction_items")
    op.drop_table("meta_extraction_items")

    op.drop_index("idx_meta_batch_project", table_name="meta_extraction_batches")
    op.drop_table("meta_extraction_batches")
