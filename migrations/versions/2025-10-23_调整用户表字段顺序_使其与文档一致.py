"""调整用户表字段顺序_使其与文档一致

Revision ID: 751636958706
Revises: 53fad9070246
Create Date: 2025-10-23 00:30:14.584213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '751636958706'
down_revision: Union[str, None] = '53fad9070246'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    调整用户表字段顺序，使其与文档一致
    
    期望的字段顺序：
    1. id, first_name, last_name, username
    2. phone_number, bio, language_code  
    3. last_activity_at
    4. is_admin, is_suspicious, is_block, is_premium, is_bot
    5. message_count
    6. created_at, created_by, updated_at, updated_by
    7. is_deleted, deleted_at, deleted_by
    """
    
    # 调整 phone_number 位置 - 移到 username 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN phone_number VARCHAR(20) COMMENT '用户的电话号码，可选字段，格式为国际标准格式（如+86138****1234）' 
        AFTER username
    """)
    
    # 调整 bio 位置 - 移到 phone_number 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN bio TEXT COMMENT '用户的个人简介，可选字段，支持长文本，来自Telegram用户资料' 
        AFTER phone_number
    """)
    
    # 调整 language_code 位置 - 移到 bio 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN language_code VARCHAR(10) COMMENT '用户的语言代码，可选字段，ISO 639-1标准（如zh、en、ru等）' 
        AFTER bio
    """)
    
    # 调整 last_activity_at 位置 - 移到 language_code 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN last_activity_at DATETIME COMMENT '用户最后活动时间，可选字段，记录用户最后一次与机器人交互的时间' 
        AFTER language_code
    """)
    
    # 调整 created_by 位置 - 移到 created_at 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN created_by BIGINT COMMENT '创建者用户ID，NULL表示系统创建' 
        AFTER created_at
    """)
    
    # 调整 updated_at 位置 - 移到 created_by 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间，创建时设置为当前时间，更新时自动更新' 
        AFTER created_by
    """)
    
    # 调整 updated_by 位置 - 移到 updated_at 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN updated_by BIGINT COMMENT '最后更新者用户ID，NULL表示系统更新' 
        AFTER updated_at
    """)


def downgrade() -> None:
    """
    回滚字段顺序调整
    
    将字段顺序恢复到调整前的状态
    """
    
    # 恢复原始顺序（按当前数据库的顺序）
    
    # 将 language_code 移回到 username 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN language_code VARCHAR(10) COMMENT '用户的语言代码，可选字段，ISO 639-1标准（如zh、en、ru等）' 
        AFTER username
    """)
    
    # 将 phone_number 移到 is_premium 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN phone_number VARCHAR(20) COMMENT '用户的电话号码，可选字段，格式为国际标准格式（如+86138****1234）' 
        AFTER is_premium
    """)
    
    # 将 bio 移到 phone_number 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN bio TEXT COMMENT '用户的个人简介，可选字段，支持长文本，来自Telegram用户资料' 
        AFTER phone_number
    """)
    
    # 将 last_activity_at 移到 updated_at 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN last_activity_at DATETIME COMMENT '用户最后活动时间，可选字段，记录用户最后一次与机器人交互的时间' 
        AFTER updated_at
    """)
    
    # 将 updated_at 移到 bio 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间，创建时设置为当前时间，更新时自动更新' 
        AFTER bio
    """)
    
    # 将 created_by 移到 deleted_at 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN created_by BIGINT COMMENT '创建者用户ID，NULL表示系统创建' 
        AFTER deleted_at
    """)
    
    # 将 updated_by 移到 created_by 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN updated_by BIGINT COMMENT '最后更新者用户ID，NULL表示系统更新' 
        AFTER created_by
    """)
