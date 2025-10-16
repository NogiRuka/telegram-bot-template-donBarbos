from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, big_int_pk, created_at


class UserModel(Base):
    """
    用户模型类，用于存储Telegram用户信息
    
    字段说明：
    - id: 用户的Telegram ID
    - first_name: 用户的名字
    - last_name: 用户的姓氏（可选）
    - username: 用户的用户名（可选）
    - language_code: 用户的语言代码（可选）
    - referrer: 推荐人信息（可选）
    - created_at: 用户创建时间
    - is_admin: 是否为管理员
    - is_suspicious: 是否为可疑用户
    - is_block: 是否被封禁
    - is_premium: 是否为高级用户
    """
    __tablename__ = "users"

    id: Mapped[big_int_pk]
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(10))
    referrer: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[created_at]

    is_admin: Mapped[bool] = mapped_column(default=False)
    is_suspicious: Mapped[bool] = mapped_column(default=False)
    is_block: Mapped[bool] = mapped_column(default=False)
    is_premium: Mapped[bool] = mapped_column(default=False)
