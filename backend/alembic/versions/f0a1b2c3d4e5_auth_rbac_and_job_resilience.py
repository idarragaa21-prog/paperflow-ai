"""auth sessions, memberships, and job resilience

Revision ID: f0a1b2c3d4e5
Revises: e2f3a4b5c6d7
Create Date: 2026-03-07

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


revision = "f0a1b2c3d4e5"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_jti", sa.String(length=128), nullable=False),
        sa.Column("token_family", sa.String(length=128), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_auth_sessions_refresh_jti", "auth_sessions", ["refresh_jti"], unique=False)
    op.create_index("ix_auth_sessions_token_family", "auth_sessions", ["token_family"], unique=False)
    op.create_index("idx_auth_sessions_user_revoked", "auth_sessions", ["user_id", "revoked_at"], unique=False)

    op.create_table(
        "project_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), server_default="viewer", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_memberships_project_user"),
    )
    op.create_index("idx_project_memberships_project_role", "project_memberships", ["project_id", "role"], unique=False)

    op.add_column("jobs", sa.Column("queue_name", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("attempt", sa.Integer(), server_default="0", nullable=False))
    op.add_column("jobs", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, user_id FROM projects")).fetchall()
    existing = {
        (row[0], row[1])
        for row in bind.execute(sa.text("SELECT project_id, user_id FROM project_memberships")).fetchall()
    }
    for project_id, user_id in rows:
        if (project_id, user_id) in existing:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO project_memberships (id, project_id, user_id, role, created_at)
                VALUES (:id, :project_id, :user_id, 'owner', now())
                """
            ),
            {"id": str(uuid.uuid4()), "project_id": str(project_id), "user_id": str(user_id)},
        )

    op.execute(
        """
        UPDATE jobs
        SET queue_name = CASE
            WHEN job_type IN ('generate_presentation', 'clinical_query') THEN 'presentations'
            ELSE 'documents'
        END
        WHERE queue_name IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("jobs", "next_retry_at")
    op.drop_column("jobs", "attempt")
    op.drop_column("jobs", "queue_name")

    op.drop_index("idx_project_memberships_project_role", table_name="project_memberships")
    op.drop_table("project_memberships")

    op.drop_index("idx_auth_sessions_user_revoked", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token_family", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_refresh_jti", table_name="auth_sessions")
    op.drop_table("auth_sessions")
