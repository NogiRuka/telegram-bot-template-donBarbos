"""Refactor notification tables

Revision ID: d59907a298a0
Revises: b22cb84fc1d0
Create Date: 2025-12-15 05:48:47.088861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd59907a298a0'
down_revision: Union[str, None] = 'b22cb84fc1d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename system_notifications to emby_notifications
    op.rename_table('system_notifications', 'emby_notifications')
    
    # 2. Add new columns to emby_notifications
    op.add_column('emby_notifications', sa.Column('target_channel_id', sa.String(64), nullable=True, comment='目标频道ID'))
    op.add_column('emby_notifications', sa.Column('target_group_id', sa.String(64), nullable=True, comment='目标群组ID'))
    
    # 3. Create emby_items table
    op.create_table(
        'emby_items',
        sa.Column('id', sa.String(64), primary_key=True, comment='Emby Item ID'),
        sa.Column('name', sa.String(255), nullable=True, comment='媒体名称'),
        sa.Column('date_created', sa.String(64), nullable=True, comment='创建时间'),
        sa.Column('overview', sa.Text(), nullable=True, comment='简介'),
        sa.Column('type', sa.String(64), nullable=True, comment='类型'),
        sa.Column('people', sa.JSON(), nullable=True, comment='人员信息'),
        sa.Column('tag_items', sa.JSON(), nullable=True, comment='标签项'),
        sa.Column('image_tags', sa.JSON(), nullable=True, comment='图片标签'),
        sa.Column('original_data', sa.JSON(), nullable=True, comment='原始数据'),
        
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # 1. Drop emby_items table
    op.drop_table('emby_items')
    
    # 2. Remove columns from emby_notifications
    op.drop_column('emby_notifications', 'target_group_id')
    op.drop_column('emby_notifications', 'target_channel_id')
    
    # 3. Rename emby_notifications back to system_notifications
    op.rename_table('emby_notifications', 'system_notifications')
