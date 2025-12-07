from __future__ import annotations
from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk
from datetime import datetime as dt


class EmbyUserModel(Base, BasicAuditMixin):
    """Emby 用户模型

    功能说明:
    - 存储从 Emby 创建/同步的用户基本信息
    - 保存完整的 `UserDto` 为 JSON 文本, 便于审计与二次处理

    输入参数:
    - 无 (ORM 模型实例化时传入字段)

    返回值:
    - 无
    """

    __tablename__ = "emby_users"

    id: Mapped[auto_int_pk]

    emby_user_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True, comment="Emby 用户ID(字符串)"
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="Emby 用户名")

    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="密码哈希 (bcrypt)")

    # 额外的时间字段(来自 Emby UserDto)
    date_created: Mapped[dt | None] = mapped_column(
        nullable=True, comment="用户创建时间(来自 Emby 的 DateCreated)"
    )
    last_login_date: Mapped[dt | None] = mapped_column(
        nullable=True, comment="最后登录时间(来自 Emby 的 LastLoginDate)"
    )
    last_activity_date: Mapped[dt | None] = mapped_column(
        nullable=True, comment="最后活动时间(来自 Emby 的 LastActivityDate)"
    )

    user_dto: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Emby 返回的 UserDto JSON 对象"
    )

    __table_args__ = (Index("idx_emby_users_name", "name"),)

    repr_cols = ("id", "emby_user_id", "name", "created_at")
