"""Rename column target_group_id to target_user_id on emby_library_new_notifications

Revision ID: 1f2a3b4c5d6e
Revises: 9caa0eddc2c3
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1f2a3b4c5d6e"
down_revision: Union[str, None] = "9caa0eddc2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将 emby_library_new_notifications.target_group_id 重命名为 target_user_id
    
    功能说明:
    - 使用 MySQL 兼容的 CHANGE COLUMN 语法进行列重命名
    
    输入参数:
    - None
    
    返回值:
    - None
    """
    op.execute(
        """
        ALTER TABLE emby_library_new_notifications
        CHANGE COLUMN target_group_id target_user_id VARCHAR(64)
        COLLATE utf8mb4_unicode_ci NULL COMMENT '需要额外通知的用户ID'
        """
    )


def downgrade() -> None:
    """将 emby_library_new_notifications.target_user_id 重命名回 target_group_id
    
    功能说明:
    - 使用 MySQL 兼容的 CHANGE COLUMN 语法进行列重命名回滚
    
    输入参数:
    - None
    
    返回值:
    - None
    """
    op.execute(
        """
        ALTER TABLE emby_library_new_notifications
        CHANGE COLUMN target_user_id target_group_id VARCHAR(64)
        COLLATE utf8mb4_unicode_ci NULL COMMENT '目标群组ID'
        """
    )

