"""新增用户扩展与历史表，并修改 users 添加附件菜单与备注

Revision ID: 7e1c9bfac1f1
Revises: 2025-10-24_添加群组消息保存配置表
Create Date: 2025-11-26 10:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '7e1c9bfac1f1'
down_revision: Union[str, None] = '60caf28f7a25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库模式

    功能说明:
    - 创建 `user_extend` 表与 `user_history` 表
    - 修改 `users` 表，新增 `added_to_attachment_menu` 与 `remark`

    输入参数:
    - 无

    返回值:
    - None
    """
    # 创建枚举类型
    userrole = sa.Enum('user', 'admin', 'owner', name='userrole')

    # user_extend 表
    op.create_table(
        'user_extend',
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户 ID'),
        sa.Column('role', userrole, nullable=False, server_default='user', comment='用户角色权限'),
        sa.Column('phone', sa.String(length=32), nullable=True, comment='电话号码（可空）'),
        sa.Column('bio', sa.String(length=512), nullable=True, comment='用户简介（可空）'),
        sa.Column('ip_list', sa.JSON(), nullable=True, comment='访问过的IP数组'),
        sa.Column('last_interaction_at', sa.DateTime(), nullable=True, comment='最后与机器人交互的时间'),
        sa.Column('remark', sa.String(length=255), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False, comment='创建时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建者ID'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False, comment='更新时间'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新者ID'),
        sa.Column('is_deleted', mysql.TINYINT(display_width=1), nullable=False, server_default='0', comment='是否删除'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        sa.Column('deleted_by', sa.BigInteger(), nullable=True, comment='删除者ID'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('idx_user_extend_role', 'user_extend', ['role'], unique=False)
    op.create_index('idx_user_extend_last_interaction', 'user_extend', ['last_interaction_at'], unique=False)

    # user_history 表
    op.create_table(
        'user_history',
        sa.Column('history_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户 ID'),
        sa.Column('is_bot', mysql.TINYINT(display_width=1), nullable=False, server_default='0', comment='是否机器人'),
        sa.Column('first_name', sa.String(length=255), nullable=False, comment='用户名'),
        sa.Column('last_name', sa.String(length=255), nullable=True, comment='姓'),
        sa.Column('username', sa.String(length=255), nullable=True, comment='用户名'),
        sa.Column('language_code', sa.String(length=32), nullable=True, comment='语言代码'),
        sa.Column('is_premium', mysql.TINYINT(display_width=1), nullable=True, comment='是否 Premium 用户'),
        sa.Column('added_to_attachment_menu', mysql.TINYINT(display_width=1), nullable=True, comment='是否加入附件菜单'),
        sa.Column('snapshot_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='快照时间'),
        sa.Column('remark', sa.String(length=255), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False, comment='创建时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建者ID'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False, comment='更新时间'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新者ID'),
        sa.Column('is_deleted', mysql.TINYINT(display_width=1), nullable=False, server_default='0', comment='是否删除'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        sa.Column('deleted_by', sa.BigInteger(), nullable=True, comment='删除者ID'),
        sa.PrimaryKeyConstraint('history_id')
    )
    op.create_index('idx_user_history_user_snapshot', 'user_history', ['user_id', 'snapshot_at'], unique=False)

    # 修改 users 表：新增列
    op.add_column('users', sa.Column('added_to_attachment_menu', mysql.TINYINT(display_width=1), nullable=True, comment='是否把 bot 加入附件菜单（可空）'))
    op.add_column('users', sa.Column('remark', sa.String(length=255), nullable=True, comment='备注'))


def downgrade() -> None:
    """回滚数据库模式

    功能说明:
    - 删除新增的表与列
    - 清理相关索引与枚举类型

    输入参数:
    - 无

    返回值:
    - None
    """
    op.drop_column('users', 'remark')
    op.drop_column('users', 'added_to_attachment_menu')
    op.drop_index('idx_user_history_user_snapshot', table_name='user_history')
    op.drop_table('user_history')
    op.drop_index('idx_user_extend_last_interaction', table_name='user_extend')
    op.drop_index('idx_user_extend_role', table_name='user_extend')
    op.drop_table('user_extend')
    # 删除枚举类型
    try:
        sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
