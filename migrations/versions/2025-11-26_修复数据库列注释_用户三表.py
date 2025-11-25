"""修复数据库列注释（users/user_history/user_extend）

Revision ID: f3a9d8b2c6a1
Revises: e4d1c7a9b2f0
Create Date: 2025-11-26 12:35:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f3a9d8b2c6a1'
down_revision: Union[str, None] = 'e4d1c7a9b2f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为用户相关三张表补齐列注释

    功能说明:
    - 确保所有列的 COMMENT 与《设计文档》一致

    输入参数:
    - 无

    返回值:
    - None
    """
    # users
    op.execute(
        """
        ALTER TABLE users
        MODIFY COLUMN id BIGINT NOT NULL COMMENT 'Telegram 用户 ID（不可为空）',
        MODIFY COLUMN is_bot TINYINT(1) NOT NULL COMMENT '是否为机器人，普通用户为0',
        MODIFY COLUMN first_name VARCHAR(255) NOT NULL COMMENT '用户名（必填）',
        MODIFY COLUMN last_name VARCHAR(255) NULL COMMENT '姓（可空）',
        MODIFY COLUMN username VARCHAR(255) NULL COMMENT '用户名（可空）',
        MODIFY COLUMN language_code VARCHAR(32) NULL COMMENT '用户语言标记（可空）',
        MODIFY COLUMN is_premium TINYINT(1) NULL COMMENT '是否 Telegram Premium 用户（可空）',
        MODIFY COLUMN added_to_attachment_menu TINYINT(1) NULL COMMENT '是否把 bot 加入附件菜单（可空）',
        MODIFY COLUMN remark TEXT NULL COMMENT '备注（长文本）',
        MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        MODIFY COLUMN created_by BIGINT NULL COMMENT '创建者ID',
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        MODIFY COLUMN updated_by BIGINT NULL COMMENT '更新者ID',
        MODIFY COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除',
        MODIFY COLUMN deleted_at DATETIME NULL COMMENT '删除时间',
        MODIFY COLUMN deleted_by BIGINT NULL COMMENT '删除者ID'
        """
    )

    # user_history
    op.execute(
        """
        ALTER TABLE user_history
        MODIFY COLUMN history_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
        MODIFY COLUMN user_id BIGINT NOT NULL COMMENT '用户 ID',
        MODIFY COLUMN is_bot TINYINT(1) NOT NULL COMMENT '是否机器人',
        MODIFY COLUMN first_name VARCHAR(255) NOT NULL COMMENT '用户名',
        MODIFY COLUMN last_name VARCHAR(255) NULL COMMENT '姓',
        MODIFY COLUMN username VARCHAR(255) NULL COMMENT '用户名',
        MODIFY COLUMN language_code VARCHAR(32) NULL COMMENT '语言代码',
        MODIFY COLUMN is_premium TINYINT(1) NULL COMMENT '是否 Premium 用户',
        MODIFY COLUMN added_to_attachment_menu TINYINT(1) NULL COMMENT '是否加入附件菜单',
        MODIFY COLUMN snapshot_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '快照时间',
        MODIFY COLUMN remark TEXT NULL COMMENT '备注（长文本）',
        MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        MODIFY COLUMN created_by BIGINT NULL COMMENT '创建者ID',
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        MODIFY COLUMN updated_by BIGINT NULL COMMENT '更新者ID',
        MODIFY COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除',
        MODIFY COLUMN deleted_at DATETIME NULL COMMENT '删除时间',
        MODIFY COLUMN deleted_by BIGINT NULL COMMENT '删除者ID'
        """
    )

    # user_extend
    op.execute(
        """
        ALTER TABLE user_extend
        MODIFY COLUMN user_id BIGINT NOT NULL COMMENT '用户 ID',
        MODIFY COLUMN role ENUM('user','admin','owner') NOT NULL DEFAULT 'user' COMMENT '用户角色权限',
        MODIFY COLUMN phone VARCHAR(32) NULL COMMENT '电话号码（可空）',
        MODIFY COLUMN bio VARCHAR(512) NULL COMMENT '用户简介（可空）',
        MODIFY COLUMN ip_list JSON NULL COMMENT '用户访问过的 IP 数组，例如 ["1.1.1.1","8.8.8.8"]',
        MODIFY COLUMN last_interaction_at DATETIME NULL COMMENT '最后与机器人交互的时间',
        MODIFY COLUMN remark TEXT NULL COMMENT '备注（长文本）',
        MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        MODIFY COLUMN created_by BIGINT NULL COMMENT '创建者 ID',
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        MODIFY COLUMN updated_by BIGINT NULL COMMENT '更新者 ID',
        MODIFY COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已删除',
        MODIFY COLUMN deleted_at DATETIME NULL COMMENT '删除时间',
        MODIFY COLUMN deleted_by BIGINT NULL COMMENT '删除者 ID'
        """
    )


def downgrade() -> None:
    """回滚列注释修复

    功能说明:
    - 保留当前注释，不执行回滚
    """
    pass

