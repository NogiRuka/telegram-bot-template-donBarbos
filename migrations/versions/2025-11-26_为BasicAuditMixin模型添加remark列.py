"""为 BasicAuditMixin 模型添加 remark 列

Revision ID: d0f4a1b9c7e2
Revises: c7a3b9b2a9c0
Create Date: 2025-11-26 12:05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd0f4a1b9c7e2'
down_revision: Union[str, None] = 'c7a3b9b2a9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 remark 列到使用 BasicAuditMixin 的表

    功能说明:
    - 在以下表中新增 `remark VARCHAR(255) NULL COMMENT '备注'`
      表：statistics、messages、configs、group_configs、user_states

    输入参数:
    - 无

    返回值:
    - None
    """
    tables = [
        'statistics',
        'messages',
        'configs',
        'group_configs',
        'user_states',
    ]
    for t in tables:
        try:
            op.add_column(t, sa.Column('remark', sa.String(length=255), nullable=True, comment='备注'))
        except Exception:
            # 已存在则忽略
            pass


def downgrade() -> None:
    """回滚新增的 remark 列

    功能说明:
    - 从上述表中删除 `remark` 列

    输入参数:
    - 无

    返回值:
    - None
    """
    tables = [
        'statistics',
        'messages',
        'configs',
        'group_configs',
        'user_states',
    ]
    for t in tables:
        try:
            op.drop_column(t, 'remark')
        except Exception:
            pass

