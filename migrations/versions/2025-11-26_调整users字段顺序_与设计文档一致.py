"""调整 users 字段顺序，与《设计文档》一致

Revision ID: c7a3b9b2a9c0
Revises: 9b3ac0d2f4a1
Create Date: 2025-11-26 11:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7a3b9b2a9c0'
down_revision: Union[str, None] = '9b3ac0d2f4a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """按文档调整 users 字段顺序

    功能说明:
    - 使用 MySQL `MODIFY COLUMN ... AFTER ...` 重排列位置
    - 排序为：id → is_bot → first_name → last_name → username → language_code → is_premium → added_to_attachment_menu → remark → created_at → created_by → updated_at → updated_by → is_deleted → deleted_at → deleted_by

    输入参数:
    - 无

    返回值:
    - None
    """
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN is_bot TINYINT(1) NOT NULL COMMENT '是否为机器人，普通用户为0' AFTER id,
        MODIFY COLUMN first_name VARCHAR(255) NOT NULL COMMENT '用户名（必填）' AFTER is_bot,
        MODIFY COLUMN last_name VARCHAR(255) NULL COMMENT '姓（可空）' AFTER first_name,
        MODIFY COLUMN username VARCHAR(255) NULL COMMENT '用户名（可空）' AFTER last_name,
        MODIFY COLUMN language_code VARCHAR(32) NULL COMMENT '用户语言标记（可空）' AFTER username,
        MODIFY COLUMN is_premium TINYINT(1) NULL COMMENT '是否 Telegram Premium 用户（可空）' AFTER language_code,
        MODIFY COLUMN added_to_attachment_menu TINYINT(1) NULL COMMENT '是否把 bot 加入附件菜单（可空）' AFTER is_premium,
        MODIFY COLUMN remark VARCHAR(255) NULL COMMENT '备注' AFTER added_to_attachment_menu,
        MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER remark,
        MODIFY COLUMN created_by BIGINT NULL COMMENT '创建者ID' AFTER created_at,
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_by,
        MODIFY COLUMN updated_by BIGINT NULL COMMENT '更新者ID' AFTER updated_at,
        MODIFY COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除' AFTER updated_by,
        MODIFY COLUMN deleted_at DATETIME NULL COMMENT '删除时间' AFTER is_deleted,
        MODIFY COLUMN deleted_by BIGINT NULL COMMENT '删除者ID' AFTER deleted_at
    """)


def downgrade() -> None:
    """回滚字段顺序调整

    功能说明:
    - 不强制回滚顺序（MySQL允许任意顺序），此处留空或按需要自定义

    输入参数:
    - 无

    返回值:
    - None
    """
    # 保持现有顺序，不做回滚
    pass

