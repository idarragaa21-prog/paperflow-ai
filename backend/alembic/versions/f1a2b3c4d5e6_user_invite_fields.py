"""user invite fields and is_admin

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2026-03-14 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("invite_token", sa.String(), nullable=True))
    op.add_column("users", sa.Column("invite_expires", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_invite_token", "users", ["invite_token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_invite_token", table_name="users")
    op.drop_column("users", "invite_expires")
    op.drop_column("users", "invite_token")
    op.drop_column("users", "is_admin")
