"""在 user_extend 表添加 emby_user_id 字段

Revision ID: b8c7a6d5e4f1
Revises: f3a9d8b2c6a1
Create Date: 2025-11-30 15:30:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "b8c7a6d5e4f1"
down_revision: str | None = "f3a9d8b2c6a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """添加 emby_user_id 列与索引

    功能说明:
    - 在 user_extend 表增加 emby_user_id 字段，用于标识 Emby 账户关联

    输入参数:
    - 无

    返回值:
    - None
    """
    op.add_column(
        "user_extend",
        sa.Column(
            "emby_user_id",
            mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
            nullable=True,
            comment="Emby 用户ID(字符串)",
        ),
    )
    op.create_index(
        "idx_user_extend_emby_user_id",
        "user_extend",
        ["emby_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """回滚 emby_user_id 列与索引

    功能说明:
    - 删除新增的 emby_user_id 字段与索引

    输入参数:
    - 无

    返回值:
    - None
    """
    try:
        op.drop_index("idx_user_extend_emby_user_id", table_name="user_extend")
    except Exception:
        pass
    try:
        op.drop_column("user_extend", "emby_user_id")
    except Exception:
        pass

