"""调整notification表字段顺序以匹配模型定义 - 使用重建表方法

Revision ID: reorder_notification_fields_v3
Revises: reorder_notification_fields_v2
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'reorder_notification_fields_v3'
down_revision = 'reorder_notification_fields_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """调整字段顺序以匹配模型定义"""
    
    # MySQL中调整字段顺序最安全的方法是重建表
    # 这样可以确保数据不丢失且顺序正确
    
    # 1. 创建临时表，字段顺序按照模型定义
    op.execute("""
        CREATE TABLE emby_notifications_new (
            id INTEGER NOT NULL AUTO_INCREMENT,
            type VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
            status VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
            item_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            item_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            item_type VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            series_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            series_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            season_number INT,
            episode_number INT,
            target_channel_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            target_group_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            payload JSON NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            created_by BIGINT,
            updated_by BIGINT,
            is_deleted TINYINT,
            deleted_at DATETIME,
            deleted_by BIGINT,
            remark TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            PRIMARY KEY (id),
            INDEX ix_emby_notifications_item_id (item_id),
            INDEX ix_emby_notifications_series_id (series_id),
            INDEX ix_emby_notifications_status (status),
            INDEX ix_emby_notifications_type (type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 2. 将数据从原表复制到新表
    op.execute("""
        INSERT INTO emby_notifications_new (
            id, type, status, item_id, item_name, item_type, series_id, series_name,
            season_number, episode_number, target_channel_id, target_group_id,
            payload, created_at, updated_at, created_by, updated_by,
            is_deleted, deleted_at, deleted_by, remark
        )
        SELECT 
            id, type, status, item_id, item_name, item_type, series_id, series_name,
            season_number, episode_number, target_channel_id, target_group_id,
            payload, created_at, updated_at, created_by, updated_by,
            is_deleted, deleted_at, deleted_by, remark
        FROM emby_notifications
    """)
    
    # 3. 删除原表
    op.execute("DROP TABLE emby_notifications")
    
    # 4. 重命名新表为原表名
    op.execute("ALTER TABLE emby_notifications_new RENAME TO emby_notifications")


def downgrade() -> None:
    """回滚操作 - 恢复原始字段顺序"""
    
    # 创建回滚用的临时表（原始顺序）
    op.execute("""
        CREATE TABLE emby_notifications_old (
            id INTEGER NOT NULL AUTO_INCREMENT,
            type VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
            status VARCHAR(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
            item_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            item_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            payload JSON NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            created_by BIGINT,
            updated_by BIGINT,
            is_deleted TINYINT,
            deleted_at DATETIME,
            deleted_by BIGINT,
            remark TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            target_channel_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            target_group_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            item_type VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            series_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            series_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            season_number INT,
            episode_number INT,
            PRIMARY KEY (id),
            INDEX ix_emby_notifications_item_id (item_id),
            INDEX ix_emby_notifications_series_id (series_id),
            INDEX ix_emby_notifications_status (status),
            INDEX ix_emby_notifications_type (type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 复制数据
    op.execute("""
        INSERT INTO emby_notifications_old (
            id, type, status, item_id, item_name, payload, created_at, updated_at,
            created_by, updated_by, is_deleted, deleted_at, deleted_by, remark,
            target_channel_id, target_group_id, item_type, series_id, series_name,
            season_number, episode_number
        )
        SELECT 
            id, type, status, item_id, item_name, payload, created_at, updated_at,
            created_by, updated_by, is_deleted, deleted_at, deleted_by, remark,
            target_channel_id, target_group_id, item_type, series_id, series_name,
            season_number, episode_number
        FROM emby_notifications
    """)
    
    # 删除新表
    op.execute("DROP TABLE emby_notifications")
    
    # 重命名回旧表名
    op.execute("ALTER TABLE emby_notifications_old RENAME TO emby_notifications")