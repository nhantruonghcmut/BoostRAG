"""Initial auth schema: users, groups, user_groups, revoked_tokens.

Revision ID: 0001_initial_auth
Revises:
Create Date: 2026-05-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_auth"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial auth tables + enums."""
    user_role = postgresql.ENUM("admin", "user", name="user_role", create_type=True)
    user_status = postgresql.ENUM(
        "pending_approval",
        "active",
        "locked",
        "disabled",
        name="user_status",
        create_type=True,
    )
    user_role.create(op.get_bind(), checkfirst=True)
    user_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "user", name="user_role", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column("access_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending_approval",
                "active",
                "locked",
                "disabled",
                name="user_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending_approval",
        ),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_groups_name", "groups", ["name"], unique=True)

    op.create_table(
        "user_groups",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column(
            "is_used_for_replay",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade() -> None:
    """Drop initial auth tables + enums."""
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.drop_table("user_groups")
    op.drop_index("ix_groups_name", table_name="groups")
    op.drop_table("groups")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    postgresql.ENUM(name="user_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
