"""重命名 library_new 表字段 target_group_id -> target_user_id

Revision ID: rename_library_new_target_user_id
Revises: add_quiz_category_table
Create Date: 2026-01-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rename_library_new_target_user_id'
down_revision = 'add_quiz_category_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """将 emby_library_new_notifications 表中的 target_group_id 重命名为 target_user_id"""
    # 注意：MySQL/MariaDB 使用 CHANGE COLUMN 语法，同时需要提供数据类型
    op.execute("""
        ALTER TABLE emby_library_new_notifications 
        CHANGE COLUMN target_group_id target_user_id VARCHAR(64) 
        COLLATE utf8mb4_unicode_ci NULL COMMENT '需要额外通知的用户ID'
    """)


def downgrade() -> None:
    """回滚：将 target_user_id 重命名回 target_group_id"""
    op.execute("""
        ALTER TABLE emby_library_new_notifications 
        CHANGE COLUMN target_user_id target_group_id VARCHAR(64) 
        COLLATE utf8mb4_unicode_ci NULL COMMENT '目标群组ID'
    """)

