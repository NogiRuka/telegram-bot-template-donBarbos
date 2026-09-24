"""新增通用命令授权表。

Revision ID: add_command_permissions
Revises: add_emby_device_history
Create Date: 2026-09-24 00:00:00
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "add_command_permissions"
down_revision: str | None = "add_emby_device_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建通用命令授权表。"""
    op.create_table(
        "command_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="获授权用户 ID"),
        sa.Column("command_name", sa.String(length=64), nullable=False, comment="授权命令名称"),
        sa.Column("scope_type", sa.String(length=16), nullable=False, comment="作用域类型"),
        sa.Column("scope_key", sa.String(length=128), nullable=False, comment="稳定作用域标识"),
        sa.Column("granted_by_user_id", sa.BigInteger(), nullable=False, comment="授权管理员 ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "scope_type IN ('global', 'group')",
            name="ck_command_permissions_scope_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "command_name",
            "scope_key",
            name="uq_command_permissions_user_command_scope",
        ),
    )
    op.create_index("ix_command_permissions_user_id", "command_permissions", ["user_id"])
    op.create_index("ix_command_permissions_command_name", "command_permissions", ["command_name"])
    op.create_index("ix_command_permissions_scope_type", "command_permissions", ["scope_type"])
    op.create_index("ix_command_permissions_scope_key", "command_permissions", ["scope_key"])
    op.create_index("ix_command_permissions_is_deleted", "command_permissions", ["is_deleted"])
    op.create_index("ix_command_permissions_created_by", "command_permissions", ["created_by"])
    op.create_index("ix_command_permissions_updated_by", "command_permissions", ["updated_by"])
    op.create_index("ix_command_permissions_deleted_by", "command_permissions", ["deleted_by"])
    op.create_index(
        "idx_command_permissions_lookup",
        "command_permissions",
        ["scope_key", "command_name", "is_deleted"],
    )


def downgrade() -> None:
    """删除通用命令授权表。"""
    op.drop_index("idx_command_permissions_lookup", table_name="command_permissions")
    op.drop_index("ix_command_permissions_deleted_by", table_name="command_permissions")
    op.drop_index("ix_command_permissions_updated_by", table_name="command_permissions")
    op.drop_index("ix_command_permissions_created_by", table_name="command_permissions")
    op.drop_index("ix_command_permissions_is_deleted", table_name="command_permissions")
    op.drop_index("ix_command_permissions_scope_key", table_name="command_permissions")
    op.drop_index("ix_command_permissions_scope_type", table_name="command_permissions")
    op.drop_index("ix_command_permissions_command_name", table_name="command_permissions")
    op.drop_index("ix_command_permissions_user_id", table_name="command_permissions")
    op.drop_table("command_permissions")
