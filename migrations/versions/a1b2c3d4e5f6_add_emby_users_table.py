"""Add Emby users table

Revision ID: a1b2c3d4e5f6
Revises: 60caf28f7a25
Create Date: 2025-11-30 12:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "60caf28f7a25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create emby_users table

    功能说明:
    - 存储 Emby 用户的基本信息与完整 UserDto JSON

    输入参数:
    - 无

    返回值:
    - None
    """
    op.create_table(
        "emby_users",
        sa.Column(
            "id",
            mysql.INTEGER(display_width=11),
            primary_key=True,
            autoincrement=True,
            nullable=False,
            comment="自增主键",
        ),
        sa.Column(
            "emby_user_id",
            mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
            nullable=False,
            comment="Emby 用户ID(字符串)",
        ),
        sa.Column(
            "name",
            mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=255),
            nullable=False,
            comment="Emby 用户名",
        ),
        sa.Column(
            "user_dto",
            mysql.TEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
            comment="Emby 返回的 UserDto JSON 字符串",
        ),
        # 审计字段
        sa.Column(
            "created_at",
            mysql.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="记录创建时间, 自动设置为当前时间",
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="记录更新时间, 创建时设置为当前时间, 更新时自动更新",
        ),
        sa.Column(
            "is_deleted",
            mysql.TINYINT(display_width=1),
            nullable=False,
            server_default="0",
            comment="软删除标志, False表示未删除, True表示已删除",
        ),
        sa.Column(
            "deleted_at",
            mysql.DATETIME(),
            nullable=True,
            comment="软删除时间, NULL表示未删除, 有值表示删除时间",
        ),
        sa.Column(
            "deleted_by",
            mysql.BIGINT(display_width=20),
            nullable=True,
            comment="删除者用户ID, NULL表示系统删除",
        ),
        sa.Column(
            "created_by",
            mysql.BIGINT(display_width=20),
            nullable=True,
            comment="创建者用户ID, NULL表示系统创建",
        ),
        sa.Column(
            "updated_by",
            mysql.BIGINT(display_width=20),
            nullable=True,
            comment="最后更新者用户ID, NULL表示系统更新",
        ),
        sa.Column(
            "version",
            mysql.INTEGER(display_width=11),
            nullable=False,
            server_default="1",
            comment="记录版本号, 用于乐观锁控制并发更新",
        ),
        sa.Column(
            "remark",
            mysql.TEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
            comment="备注(长文本)",
        ),
        mysql_collate="utf8mb4_unicode_ci",
        mysql_default_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_emby_users_emby_user_id", "emby_users", ["emby_user_id"], unique=True)
    op.create_index("idx_emby_users_name", "emby_users", ["name"], unique=False)


def downgrade() -> None:
    """Drop emby_users table

    功能说明:
    - 回滚时删除表及索引

    输入参数:
    - 无

    返回值:
    - None
    """
    op.drop_index("ix_emby_users_emby_user_id", table_name="emby_users")
    op.drop_index("idx_emby_users_name", table_name="emby_users")
    op.drop_table("emby_users")

