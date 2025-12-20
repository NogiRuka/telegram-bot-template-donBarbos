"""修复通知状态字段默认值问题

Revision ID: c01e32e4ae81
Revises: 5390f12a19ad
Create Date: 2025-12-21 01:39:00.419429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'c01e32e4ae81'
down_revision: Union[str, None] = '5390f12a19ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级操作：移除status字段的默认值，允许为NULL"""
    # 修改status字段，移除默认值，允许为NULL
    op.alter_column('emby_notifications', 'status',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=32),
               nullable=True,
               existing_comment='状态: pending_completion/pending_review/sent/failed')


def downgrade() -> None:
    """降级操作：恢复status字段的默认值，不允许为NULL"""
    # 恢复status字段的默认值，不允许为NULL
    op.alter_column('emby_notifications', 'status',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=32),
               nullable=False,
               existing_comment='状态: pending_completion/pending_review/sent/failed')