"""添加library_new通知表

Revision ID: 9caa0eddc2c3
Revises: 808f3688b0c8
Create Date: 2026-01-03 18:14:01.655019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9caa0eddc2c3'
down_revision: Union[str, None] = '808f3688b0c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 检查表是否存在，如果不存在则创建
    conn = op.get_bind()
    result = conn.execute(sa.text("SHOW TABLES LIKE 'emby_library_new_notifications'"))
    if not result.fetchone():
        # 创建新的library_new通知表
        op.create_table('emby_library_new_notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.BigInteger(), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True, comment='通知标题'),
        sa.Column('type', sa.String(length=64), nullable=False, comment='通知类型'),
        sa.Column('status', sa.String(length=32), nullable=True, comment='状态: pending_completion/pending_review/sent/failed'),
        sa.Column('item_id', sa.String(length=64), nullable=True, comment='Emby Item ID'),
        sa.Column('item_name', sa.String(length=255), nullable=True, comment='媒体名称'),
        sa.Column('item_type', sa.String(length=64), nullable=True, comment='媒体类型'),
        sa.Column('series_id', sa.String(length=64), nullable=True, comment='剧集ID (SeriesId)'),
        sa.Column('series_name', sa.String(length=255), nullable=True, comment='剧集名称'),
        sa.Column('season_number', sa.Integer(), nullable=True, comment='季号 (ParentIndexNumber)'),
        sa.Column('episode_number', sa.Integer(), nullable=True, comment='集号 (IndexNumber)'),
        sa.Column('target_channel_id', sa.String(length=64), nullable=True, comment='目标频道ID'),
        sa.Column('target_group_id', sa.String(length=64), nullable=True, comment='目标群组ID'),
        sa.Column('payload', sa.JSON(), nullable=False, comment='原始 Webhook 数据'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_emby_library_new_notifications_item_id'), 'emby_library_new_notifications', ['item_id'], unique=False)
        op.create_index(op.f('ix_emby_library_new_notifications_series_id'), 'emby_library_new_notifications', ['series_id'], unique=False)
        op.create_index(op.f('ix_emby_library_new_notifications_status'), 'emby_library_new_notifications', ['status'], unique=False)
        op.create_index(op.f('ix_emby_library_new_notifications_type'), 'emby_library_new_notifications', ['type'], unique=False)


def downgrade() -> None:
    # 删除library_new通知表
    op.drop_index(op.f('ix_emby_library_new_notifications_type'), table_name='emby_library_new_notifications')
    op.drop_index(op.f('ix_emby_library_new_notifications_status'), table_name='emby_library_new_notifications')
    op.drop_index(op.f('ix_emby_library_new_notifications_series_id'), table_name='emby_library_new_notifications')
    op.drop_index(op.f('ix_emby_library_new_notifications_item_id'), table_name='emby_library_new_notifications')
    op.drop_table('emby_library_new_notifications')