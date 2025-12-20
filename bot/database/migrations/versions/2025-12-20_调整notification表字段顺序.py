"""调整notification表字段顺序以匹配模型定义

Revision ID: reorder_notification_fields
Revises: 2025-12-20_添加剧集相关字段到notificationmodel和embyitemmodel
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'reorder_notification_fields'
down_revision = '2025-12-20_添加剧集相关字段到notificationmodel和embyitemmodel'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """调整字段顺序以匹配模型定义"""
    
    # MySQL不支持直接调整列顺序，需要通过重建表来实现
    # 这里使用ALTER TABLE MODIFY COLUMN来调整列顺序
    
    # 1. 首先将item_type字段移动到item_name之后
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN item_type VARCHAR(64) COLLATE utf8mb4_unicode_ci NULL COMMENT '媒体类型' 
        AFTER item_name
    """)
    
    # 2. 将剧集相关字段按顺序移动到payload之前
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN series_id VARCHAR(64) COLLATE utf8mb4_unicode_ci NULL COMMENT '剧集ID (SeriesId)' 
        AFTER item_type
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN series_name VARCHAR(255) COLLATE utf8mb4_unicode_ci NULL COMMENT '剧集名称' 
        AFTER series_id
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN season_number INT NULL COMMENT '季号 (ParentIndexNumber)' 
        AFTER series_name
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN episode_number INT NULL COMMENT '集号 (IndexNumber)' 
        AFTER season_number
    """)


def downgrade() -> None:
    """回滚操作 - 将字段移回末尾"""
    
    # 将剧集相关字段移回末尾
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN episode_number INT NULL COMMENT '集号 (IndexNumber)' 
        AFTER target_group_id
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN season_number INT NULL COMMENT '季号 (ParentIndexNumber)' 
        AFTER episode_number
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN series_name VARCHAR(255) COLLATE utf8mb4_unicode_ci NULL COMMENT '剧集名称' 
        AFTER season_number
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN series_id VARCHAR(64) COLLATE utf8mb4_unicode_ci NULL COMMENT '剧集ID (SeriesId)' 
        AFTER series_name
    """)
    
    op.execute("""
        ALTER TABLE emby_notifications 
        MODIFY COLUMN item_type VARCHAR(64) COLLATE utf8mb4_unicode_ci NULL COMMENT '媒体类型' 
        AFTER series_id
    """)