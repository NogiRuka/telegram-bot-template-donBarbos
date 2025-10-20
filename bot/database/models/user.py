from __future__ import annotations
import datetime

from sqlalchemy import String, Text, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, big_int_pk, created_at, updated_at


class UserModel(Base):
    """
    用户模型类，用于存储Telegram用户信息
    
    字段说明：
    - id: 用户的Telegram ID
    - first_name: 用户的名字
    - last_name: 用户的姓氏（可选）
    - username: 用户的用户名（可选）
    - phone_number: 用户的电话号码（可选）
    - bio: 用户简介（可选）
    - language_code: 用户的语言代码（可选）
    - referrer: 推荐人信息（可选）
    - referrer_id: 推荐人ID（可选）
    - created_at: 用户创建时间
    - updated_at: 用户更新时间
    - last_activity_at: 最后活动时间
    - is_admin: 是否为管理员
    - is_suspicious: 是否为可疑用户
    - is_block: 是否被封禁
    - is_premium: 是否为高级用户
    - is_bot: 是否为机器人
    - message_count: 消息数量统计
    """
    __tablename__ = "users"

    # 基本信息
    id: Mapped[big_int_pk]
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    
    # 推荐系统
    referrer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    
    # 时间戳
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
    last_activity_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True, index=True)
    
    # 状态标志
    is_admin: Mapped[bool] = mapped_column(default=False, index=True)
    is_suspicious: Mapped[bool] = mapped_column(default=False, index=True)
    is_block: Mapped[bool] = mapped_column(default=False, index=True)
    is_premium: Mapped[bool] = mapped_column(default=False, index=True)
    is_bot: Mapped[bool] = mapped_column(default=False)
    
    # 统计信息
    message_count: Mapped[int] = mapped_column(default=0)
    
    # 索引定义
    __table_args__ = (
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_updated_at', 'updated_at'),
        Index('idx_users_last_activity', 'last_activity_at'),
        Index('idx_users_referrer_id', 'referrer_id'),
        Index('idx_users_status', 'is_block', 'is_suspicious'),
        Index('idx_users_admin_premium', 'is_admin', 'is_premium'),
    )
    
    # 用于repr显示的列
    repr_cols = ('id', 'username', 'first_name', 'is_admin', 'is_premium')
