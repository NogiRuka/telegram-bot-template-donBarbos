"""正确调整用户表字段顺序_完整重排

Revision ID: 61c45d421fa3
Revises: 751636958706
Create Date: 2025-10-23 00:32:25.778522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61c45d421fa3'
down_revision: Union[str, None] = '751636958706'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    正确调整用户表字段顺序，使其与文档完全一致
    
    期望的字段顺序：
    1. id (主键，保持第一位)
    2. first_name, last_name, username
    3. phone_number, bio, language_code, last_activity_at
    4. is_admin, is_suspicious, is_block, is_premium, is_bot
    5. message_count
    6. created_at, created_by, updated_at, updated_by
    7. is_deleted, deleted_at, deleted_by
    """
    
    # 按照期望顺序重新排列字段
    # 注意：MySQL的MODIFY COLUMN ... AFTER语法会将字段移动到指定字段之后
    
    # 1. 确保基本信息字段顺序正确 (id已经是第一个)
    # first_name, last_name, username 已经在正确位置
    
    # 2. 移动 phone_number 到 username 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN phone_number VARCHAR(20) COMMENT '用户的电话号码，可选字段，格式为国际标准格式（如+86138****1234）' 
        AFTER username
    """)
    
    # 3. 移动 bio 到 phone_number 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN bio TEXT COMMENT '用户的个人简介，可选字段，支持长文本，来自Telegram用户资料' 
        AFTER phone_number
    """)
    
    # 4. 移动 language_code 到 bio 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN language_code VARCHAR(10) COMMENT '用户的语言代码，可选字段，ISO 639-1标准（如zh、en、ru等）' 
        AFTER bio
    """)
    
    # 5. 移动 last_activity_at 到 language_code 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN last_activity_at DATETIME COMMENT '用户最后活动时间，可选字段，记录用户最后一次与机器人交互的时间' 
        AFTER language_code
    """)
    
    # 6. 移动状态字段到正确位置
    # 移动 is_admin 到 last_activity_at 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN is_admin TINYINT(1) NOT NULL COMMENT '管理员标志，默认False，True表示该用户具有管理员权限' 
        AFTER last_activity_at
    """)
    
    # 移动 is_suspicious 到 is_admin 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN is_suspicious TINYINT(1) NOT NULL COMMENT '可疑用户标志，默认False，True表示该用户被标记为可疑，需要特别关注' 
        AFTER is_admin
    """)
    
    # 移动 is_block 到 is_suspicious 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN is_block TINYINT(1) NOT NULL COMMENT '封禁状态标志，默认False，True表示该用户被封禁，无法使用机器人功能' 
        AFTER is_suspicious
    """)
    
    # 移动 is_premium 到 is_block 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN is_premium TINYINT(1) NOT NULL COMMENT '高级用户标志，默认False，True表示该用户是Telegram Premium用户' 
        AFTER is_block
    """)
    
    # 移动 is_bot 到 is_premium 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN is_bot TINYINT(1) NOT NULL DEFAULT 0 COMMENT '机器人标志，默认False，True表示该账号是机器人而非真实用户' 
        AFTER is_premium
    """)
    
    # 7. 移动 message_count 到 is_bot 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN message_count INT NOT NULL DEFAULT 0 COMMENT '消息计数，默认0，记录用户发送给机器人的消息总数，用于统计分析' 
        AFTER is_bot
    """)
    
    # 8. 移动审计字段到正确位置
    # 移动 created_at 到 message_count 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间，自动设置为当前时间' 
        AFTER message_count
    """)
    
    # 移动 created_by 到 created_at 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN created_by BIGINT COMMENT '创建者用户ID，NULL表示系统创建' 
        AFTER created_at
    """)
    
    # 移动 updated_at 到 created_by 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间，创建时设置为当前时间，更新时自动更新' 
        AFTER created_by
    """)
    
    # 移动 updated_by 到 updated_at 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN updated_by BIGINT COMMENT '最后更新者用户ID，NULL表示系统更新' 
        AFTER updated_at
    """)
    
    # 9. 移动软删除字段到最后
    # 移动 is_deleted 到 updated_by 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN is_deleted TINYINT(1) NOT NULL COMMENT '软删除标志，False表示未删除，True表示已删除' 
        AFTER updated_by
    """)
    
    # 移动 deleted_at 到 is_deleted 之后
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN deleted_at DATETIME COMMENT '软删除时间，NULL表示未删除，有值表示删除时间' 
        AFTER is_deleted
    """)
    
    # 移动 deleted_by 到 deleted_at 之后（最后一个字段）
    op.execute("""
        ALTER TABLE users 
        MODIFY COLUMN deleted_by BIGINT COMMENT '删除者用户ID，NULL表示系统删除' 
        AFTER deleted_at
    """)


def downgrade() -> None:
    """
    回滚字段顺序调整
    
    将字段顺序恢复到调整前的状态
    """
    
    # 这里可以添加回滚逻辑，但由于字段顺序调整不影响数据，
    # 通常不需要实现复杂的回滚逻辑
    pass
