"""调整notification表字段顺序以匹配模型定义

Revision ID: reorder_notification_fields_v2
Revises: reorder_notification_fields
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'reorder_notification_fields_v2'
down_revision = 'reorder_notification_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """调整字段顺序以匹配模型定义"""
    
    # 使用CHANGE COLUMN语法来调整字段顺序
    # 注意：MySQL需要重新定义完整的列定义
    
    # 1. 将item_type移动到item_name之后
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN item_type item_type VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '媒体类型' 
        AFTER item_name
    """)
    
    # 2. 将series_id移动到item_type之后
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN series_id series_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '剧集ID (SeriesId)' 
        AFTER item_type
    """)
    
    # 3. 将series_name移动到series_id之后
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN series_name series_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '剧集名称' 
        AFTER series_id
    """)
    
    # 4. 将season_number移动到series_name之后
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN season_number season_number INT NULL DEFAULT NULL COMMENT '季号 (ParentIndexNumber)' 
        AFTER series_name
    """)
    
    # 5. 将episode_number移动到season_number之后
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN episode_number episode_number INT NULL DEFAULT NULL COMMENT '集号 (IndexNumber)' 
        AFTER season_number
    """)


def downgrade() -> None:
    """回滚操作 - 将字段移回末尾"""
    
    # 将字段移回target_group_id之后
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN episode_number episode_number INT NULL DEFAULT NULL COMMENT '集号 (IndexNumber)' 
        AFTER target_group_id
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN season_number season_number INT NULL DEFAULT NULL COMMENT '季号 (ParentIndexNumber)' 
        AFTER episode_number
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN series_name series_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '剧集名称' 
        AFTER season_number
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN series_id series_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '剧集ID (SeriesId)' 
        AFTER series_name
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        CHANGE COLUMN item_type item_type VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '媒体类型' 
        AFTER series_id
    """)