"""添加emby_items表的episode_data字段

Revision ID: 5390f12a19ad
Revises: b36134ce4a5f
Create Date: 2025-12-21 00:16:13.198279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '5390f12a19ad'
down_revision: Union[str, None] = 'b36134ce4a5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加episode_data字段到emby_items表
    op.add_column('emby_items', sa.Column('episode_data', mysql.JSON(), nullable=True, comment='剧集详情数据(JSON格式，包含所有剧集信息)'))


def downgrade() -> None:
    # 删除episode_data字段
    op.drop_column('emby_items', 'episode_data')