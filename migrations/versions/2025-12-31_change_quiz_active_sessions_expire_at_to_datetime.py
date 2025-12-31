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
down_revision: Union[str, None] = '72db368f1634'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：将整数时间戳转换为 DATETIME（精确到秒）
    
    步骤:
    1) 新增临时列 expire_at_dt (DATETIME)
    2) 用 FROM_UNIXTIME(expire_at) 转换并写入临时列
    3) 删除原索引与原列 expire_at
    4) 将临时列改名为 expire_at
    5) 恢复索引
    """
    # 1) 新增临时列
    op.add_column('quiz_active_sessions', sa.Column('expire_at_dt', sa.DateTime(), nullable=False, comment='过期时间（精确到秒）'))
    # 2) 数据转换
    op.execute("UPDATE quiz_active_sessions SET expire_at_dt = FROM_UNIXTIME(expire_at)")
    # 3) 删除旧索引与旧列
    with op.batch_alter_table('quiz_active_sessions') as batch_op:
        batch_op.drop_index('idx_quiz_sessions_expire')
        batch_op.drop_column('expire_at')
    # 4) 重命名临时列为正式列
    with op.batch_alter_table('quiz_active_sessions') as batch_op:
        batch_op.alter_column('expire_at_dt', new_column_name='expire_at', existing_type=sa.DateTime(), nullable=False, existing_nullable=False, comment='过期时间（精确到秒）')
        # 5) 恢复索引
        batch_op.create_index('idx_quiz_sessions_expire', ['expire_at'], unique=False)


def downgrade() -> None:
    """降级：将 DATETIME 转换回整数时间戳
    
    步骤:
    1) 新增临时列 expire_at_ts (INT)
    2) 用 UNIX_TIMESTAMP(expire_at) 转换并写入临时列
    3) 删除索引与原列 expire_at
    4) 将临时列改名为 expire_at
    5) 恢复索引
    """
    # 1) 新增临时列
    op.add_column('quiz_active_sessions', sa.Column('expire_at_ts', sa.Integer(), nullable=False, comment='过期时间戳'))
    # 2) 数据转换
    op.execute("UPDATE quiz_active_sessions SET expire_at_ts = UNIX_TIMESTAMP(expire_at)")
    # 3) 删除旧索引与旧列
    with op.batch_alter_table('quiz_active_sessions') as batch_op:
        batch_op.drop_index('idx_quiz_sessions_expire')
        batch_op.drop_column('expire_at')
    # 4) 重命名临时列为正式列
    with op.batch_alter_table('quiz_active_sessions') as batch_op:
        batch_op.alter_column('expire_at_ts', new_column_name='expire_at', existing_type=sa.Integer(), nullable=False, existing_nullable=False, comment='过期时间戳')
        # 5) 恢复索引
        batch_op.create_index('idx_quiz_sessions_expire', ['expire_at'], unique=False)
