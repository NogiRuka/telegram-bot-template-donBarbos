"""remark 字段类型改为 TEXT（所有使用 BasicAuditMixin 的表）

Revision ID: e4d1c7a9b2f0
Revises: d0f4a1b9c7e2
Create Date: 2025-11-26 12:18:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4d1c7a9b2f0'
down_revision: Union[str, None] = 'd0f4a1b9c7e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将 remark 列改为 TEXT 类型

    功能说明:
    - 修改以下表的 `remark` 列类型为 TEXT：
      users、user_history、user_extend、statistics、messages、configs、group_configs、user_states

    输入参数:
    - 无

    返回值:
    - None
    """
    for t in [
        'users',
        'user_history',
        'user_extend',
        'statistics',
        'messages',
        'configs',
        'group_configs',
        'user_states',
    ]:
        try:
            op.alter_column(t, 'remark', type_=sa.Text(), existing_nullable=True)
        except Exception:
            pass


def downgrade() -> None:
    """回滚 remark 列类型为 VARCHAR(255)

    功能说明:
    - 将上述表的 `remark` 列类型恢复为 VARCHAR(255)

    输入参数:
    - 无

    返回值:
    - None
    """
    for t in [
        'users',
        'user_history',
        'user_extend',
        'statistics',
        'messages',
        'configs',
        'group_configs',
        'user_states',
    ]:
        try:
            op.alter_column(t, 'remark', type_=sa.String(length=255), existing_nullable=True)
        except Exception:
            pass

