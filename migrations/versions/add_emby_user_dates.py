"""添加 Emby 用户日期字段

Revision ID: add_emby_user_dates
Revises: a1b2c3d4e5f6
Create Date: 2025-12-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_emby_user_dates"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # emby_users 表新增日期字段
    op.add_column(
        "emby_users",
        sa.Column("date_created", sa.DateTime(), nullable=True, comment="用户创建时间(Emby DateCreated)"),
    )
    op.add_column(
        "emby_users",
        sa.Column("last_login_date", sa.DateTime(), nullable=True, comment="最后登录时间(Emby LastLoginDate)"),
    )
    op.add_column(
        "emby_users",
        sa.Column("last_activity_date", sa.DateTime(), nullable=True, comment="最后活动时间(Emby LastActivityDate)"),
    )

    # emby_user_history 表新增日期字段快照
    op.add_column(
        "emby_user_history",
        sa.Column("date_created", sa.DateTime(), nullable=True, comment="用户创建时间快照(Emby DateCreated)"),
    )
    op.add_column(
        "emby_user_history",
        sa.Column("last_login_date", sa.DateTime(), nullable=True, comment="最后登录时间快照(Emby LastLoginDate)"),
    )
    op.add_column(
        "emby_user_history",
        sa.Column(
            "last_activity_date",
            sa.DateTime(),
            nullable=True,
            comment="最后活动时间快照(Emby LastActivityDate)",
        ),
    )


def downgrade() -> None:
    op.drop_column("emby_users", "last_activity_date")
    op.drop_column("emby_users", "last_login_date")
    op.drop_column("emby_users", "date_created")

    op.drop_column("emby_user_history", "last_activity_date")
    op.drop_column("emby_user_history", "last_login_date")
    op.drop_column("emby_user_history", "date_created")

