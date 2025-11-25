"""调整 users 表为《设计文档》最终版

Revision ID: 9b3ac0d2f4a1
Revises: 7e1c9bfac1f1
Create Date: 2025-11-26 11:05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '9b3ac0d2f4a1'
down_revision: Union[str, None] = '7e1c9bfac1f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级 users 表结构

    功能说明:
    - 删除非 aiogram User 字段：phone_number、bio、last_activity_at、is_admin、is_suspicious、is_block、message_count
    - 删除相关索引：idx_users_last_activity、idx_users_status、idx_users_admin_premium，以及 ix_* 索引
    - 调整 language_code 长度为 32

    输入参数:
    - 无

    返回值:
    - None
    """
    # 删除索引（存在才删除）
    for idx_name in [
        'idx_users_last_activity',
        'idx_users_status',
        'idx_users_admin_premium',
        op.f('ix_users_last_activity_at'),
        op.f('ix_users_is_admin'),
        op.f('ix_users_is_suspicious'),
        op.f('ix_users_is_block'),
    ]:
        try:
            op.drop_index(idx_name, table_name='users')
        except Exception:
            pass

    # 删除列（存在才删除）
    for col in [
        'phone_number',
        'bio',
        'last_activity_at',
        'is_admin',
        'is_suspicious',
        'is_block',
        'message_count',
    ]:
        try:
            op.drop_column('users', col)
        except Exception:
            pass

    # 调整 language_code 长度
    try:
        op.alter_column('users', 'language_code', type_=sa.String(length=32), existing_nullable=True)
    except Exception:
        pass


def downgrade() -> None:
    """回滚 users 表结构

    功能说明:
    - 恢复删除的列与索引（尽量）

    输入参数:
    - 无

    返回值:
    - None
    """
    # 恢复列（不设置默认值，由应用层填充）
    for col, ddl in [
        ('phone_number', sa.Column('phone_number', sa.String(length=20), nullable=True)),
        ('bio', sa.Column('bio', sa.Text(), nullable=True)),
        ('last_activity_at', sa.Column('last_activity_at', sa.DateTime(), nullable=True)),
        ('is_admin', sa.Column('is_admin', mysql.TINYINT(display_width=1), nullable=False, server_default='0')),
        ('is_suspicious', sa.Column('is_suspicious', mysql.TINYINT(display_width=1), nullable=False, server_default='0')),
        ('is_block', sa.Column('is_block', mysql.TINYINT(display_width=1), nullable=False, server_default='0')),
        ('message_count', sa.Column('message_count', sa.Integer(), nullable=False, server_default='0')),
    ]:
        try:
            op.add_column('users', ddl)
        except Exception:
            pass

    # 恢复索引（尽量）
    try:
        op.create_index('idx_users_last_activity', 'users', ['last_activity_at'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('idx_users_status', 'users', ['is_block', 'is_suspicious'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('idx_users_admin_premium', 'users', ['is_admin', 'is_premium'], unique=False)
    except Exception:
        pass

