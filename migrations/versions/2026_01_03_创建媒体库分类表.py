"""
创建媒体库分类表

修订 ID: 2026_01_03_创建媒体库分类表
创建时间: 2026-01-03 19:50

功能说明:
- 创建emby_media_categories表用于存储媒体库分类
- 支持分类的启用/禁用和排序功能
"""

from alembic import op
import sqlalchemy as sa


# 修订信息
revision = '2026_01_03_创建媒体库分类表'
down_revision = '9caa0eddc2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库
    
    功能说明:
    - 创建emby_media_categories表
    - 添加索引以提高查询性能
    """
    # 检查表是否存在，如果不存在则创建
    conn = op.get_bind()
    result = conn.execute(sa.text("SHOW TABLES LIKE 'emby_media_categories'"))
    if not result.fetchone():
        # 创建媒体库分类表
        op.create_table('emby_media_categories',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.BigInteger(), nullable=True),
            sa.Column('updated_by', sa.BigInteger(), nullable=True),
            sa.Column('is_deleted', sa.Boolean(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('deleted_by', sa.BigInteger(), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            sa.Column('name', sa.String(length=64), nullable=False, comment='分类名称'),
            sa.Column('description', sa.String(length=255), nullable=True, comment='分类描述'),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, comment='是否启用'),
            sa.Column('sort_order', sa.Integer(), nullable=False, comment='排序顺序'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # 创建索引
        op.create_index(op.f('ix_emby_media_categories_name'), 'emby_media_categories', ['name'], unique=True)
        op.create_index(op.f('ix_emby_media_categories_is_enabled'), 'emby_media_categories', ['is_enabled'], unique=False)
        op.create_index(op.f('ix_emby_media_categories_sort_order'), 'emby_media_categories', ['sort_order'], unique=False)


def downgrade() -> None:
    """降级数据库
    
    功能说明:
    - 删除emby_media_categories表及相关索引
    """
    # 删除索引
    op.drop_index(op.f('ix_emby_media_categories_sort_order'), table_name='emby_media_categories')
    op.drop_index(op.f('ix_emby_media_categories_is_enabled'), table_name='emby_media_categories')
    op.drop_index(op.f('ix_emby_media_categories_name'), table_name='emby_media_categories')
    
    # 删除表
    op.drop_table('emby_media_categories')