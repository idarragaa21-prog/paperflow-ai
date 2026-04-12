"""expand extracted effect-size contract for matrix/dataset v2

Revision ID: c4d5e6f7a8b9
Revises: b3d4e5f6a7b8
Create Date: 2026-04-12 18:20:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extracted_effect_sizes",
        sa.Column("outcome_type", sa.String(length=32), nullable=False, server_default=sa.text("'binary'")),
    )
    op.add_column("extracted_effect_sizes", sa.Column("outcome_unit", sa.String(length=64), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("comparator_type", sa.String(length=64), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("effect_direction", sa.String(length=32), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("events_total", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("total_n", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("effect_value", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("effect_se", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("weight", sa.Float(), nullable=True))

    op.add_column("extracted_effect_sizes", sa.Column("n_intervention", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("n_control", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("mean_intervention", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("sd_intervention", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("mean_control", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("sd_control", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("median_intervention", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("iqr_intervention", sa.String(length=64), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("median_control", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("iqr_control", sa.String(length=64), nullable=True))

    op.add_column("extracted_effect_sizes", sa.Column("followup_time", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("followup_unit", sa.String(length=32), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("person_time_intervention", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("person_time_control", sa.Float(), nullable=True))

    op.add_column("extracted_effect_sizes", sa.Column("tp", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("fp", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("fn", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("tn", sa.Integer(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("sensitivity_value", sa.Float(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("specificity_value", sa.Float(), nullable=True))

    op.add_column("extracted_effect_sizes", sa.Column("subgroup_label", sa.String(length=128), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("subgroup_level", sa.String(length=128), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("subgroup_order", sa.Integer(), nullable=True))
    op.add_column(
        "extracted_effect_sizes",
        sa.Column("sensitivity_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("extracted_effect_sizes", sa.Column("sensitivity_reason", sa.Text(), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("analysis_population", sa.String(length=64), nullable=True))
    op.add_column("extracted_effect_sizes", sa.Column("model_type", sa.String(length=32), nullable=True))
    op.add_column(
        "extracted_effect_sizes",
        sa.Column("covariates_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("extracted_effect_sizes", "covariates_json")
    op.drop_column("extracted_effect_sizes", "model_type")
    op.drop_column("extracted_effect_sizes", "analysis_population")
    op.drop_column("extracted_effect_sizes", "sensitivity_reason")
    op.drop_column("extracted_effect_sizes", "sensitivity_flag")
    op.drop_column("extracted_effect_sizes", "subgroup_order")
    op.drop_column("extracted_effect_sizes", "subgroup_level")
    op.drop_column("extracted_effect_sizes", "subgroup_label")

    op.drop_column("extracted_effect_sizes", "specificity_value")
    op.drop_column("extracted_effect_sizes", "sensitivity_value")
    op.drop_column("extracted_effect_sizes", "tn")
    op.drop_column("extracted_effect_sizes", "fn")
    op.drop_column("extracted_effect_sizes", "fp")
    op.drop_column("extracted_effect_sizes", "tp")

    op.drop_column("extracted_effect_sizes", "person_time_control")
    op.drop_column("extracted_effect_sizes", "person_time_intervention")
    op.drop_column("extracted_effect_sizes", "followup_unit")
    op.drop_column("extracted_effect_sizes", "followup_time")

    op.drop_column("extracted_effect_sizes", "iqr_control")
    op.drop_column("extracted_effect_sizes", "median_control")
    op.drop_column("extracted_effect_sizes", "iqr_intervention")
    op.drop_column("extracted_effect_sizes", "median_intervention")
    op.drop_column("extracted_effect_sizes", "sd_control")
    op.drop_column("extracted_effect_sizes", "mean_control")
    op.drop_column("extracted_effect_sizes", "sd_intervention")
    op.drop_column("extracted_effect_sizes", "mean_intervention")
    op.drop_column("extracted_effect_sizes", "n_control")
    op.drop_column("extracted_effect_sizes", "n_intervention")

    op.drop_column("extracted_effect_sizes", "weight")
    op.drop_column("extracted_effect_sizes", "effect_se")
    op.drop_column("extracted_effect_sizes", "effect_value")
    op.drop_column("extracted_effect_sizes", "total_n")
    op.drop_column("extracted_effect_sizes", "events_total")
    op.drop_column("extracted_effect_sizes", "effect_direction")
    op.drop_column("extracted_effect_sizes", "comparator_type")
    op.drop_column("extracted_effect_sizes", "outcome_unit")
    op.drop_column("extracted_effect_sizes", "outcome_type")
