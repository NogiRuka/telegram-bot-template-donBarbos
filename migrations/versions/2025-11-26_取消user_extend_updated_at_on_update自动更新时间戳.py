"""取消 user_extend.updated_at 的 ON UPDATE 自动更新时间戳

Revision ID: a1b9c7d2e4f0
Revises: f3a9d8b2c6a1
Create Date: 2025-11-26 13:03:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b9c7d2e4f0'
down_revision: Union[str, None] = 'f3a9d8b2c6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """修改 user_extend.updated_at，移除 ON UPDATE CURRENT_TIMESTAMP

    功能说明:
    - 保留默认值 CURRENT_TIMESTAMP，但取消自动更新时间戳
    """
    op.execute(
        """
        ALTER TABLE user_extend 
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间（不随交互自动更新）'
        """
    )


def downgrade() -> None:
    """恢复 ON UPDATE CURRENT_TIMESTAMP 设置"""
    op.execute(
        """
        ALTER TABLE user_extend 
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
        """
    )

