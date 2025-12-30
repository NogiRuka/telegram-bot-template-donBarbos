"""Add quiz category table

Revision ID: add_quiz_category_table
Revises: reorder_notification_fields_v3
Create Date: 2025-12-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_quiz_category_table'
down_revision = 'reorder_notification_fields_v3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create quiz_categories table
    op.create_table('quiz_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        comment='问答分类表'
    )

    # Insert default categories
    # 影视：1.国产剧 2.台剧 3.泰剧 4.韩剧 5.日剧 6.欧美剧 7.其他剧
    # 8.动漫 9.漫画 10.钙片 11.小说 12.广播剧 13.游戏 14.音乐 15.其他
    categories = [
        (1, '国产剧', 1),
        (2, '台剧', 2),
        (3, '泰剧', 3),
        (4, '韩剧', 4),
        (5, '日剧', 5),
        (6, '欧美剧', 6),
        (7, '其他剧', 7),
        (8, '动漫', 8),
        (9, '漫画', 9),
        (10, '钙片', 10),
        (11, '小说', 11),
        (12, '广播剧', 12),
        (13, '游戏', 13),
        (14, '音乐', 14),
        (15, '其他', 15),
    ]
    
    # Bulk insert
    op.bulk_insert(
        sa.table('quiz_categories',
            sa.column('id', sa.Integer),
            sa.column('name', sa.String),
            sa.column('sort_order', sa.Integer)
        ),
        [
            {'id': c[0], 'name': c[1], 'sort_order': c[2]}
            for c in categories
        ]
    )


def downgrade() -> None:
    op.drop_table('quiz_categories')
