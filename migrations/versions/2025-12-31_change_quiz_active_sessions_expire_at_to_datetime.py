"""将 quiz_active_sessions.expire_at 从整数时间戳改为 DATETIME(精确到秒)

Revision ID: change_expire_at_datetime
Revises: 474aa6a
Create Date: 2025-12-31 15:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'change_expire_at_datetime'
down_revision: Union[str, None] = '474aa6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：修改列类型为 DATETIME 并保留索引"""
    op.alter_column(
        'quiz_active_sessions',
        'expire_at',
        existing_type=sa.Integer(),
        type_=sa.DateTime(),
        existing_nullable=False,
        nullable=False,
        comment='过期时间（精确到秒）'
    )


def downgrade() -> None:
    """降级：恢复为整数时间戳"""
    op.alter_column(
        'quiz_active_sessions',
        'expire_at',
        existing_type=sa.DateTime(),
        type_=sa.Integer(),
        existing_nullable=False,
        nullable=False,
        comment='过期时间戳'
    )

