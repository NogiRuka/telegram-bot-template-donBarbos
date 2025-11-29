from __future__ import annotations
from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class EmbyUserHistoryModel(Base, BasicAuditMixin):
    """Emby 用户历史模型

    功能说明:
    - 记录 Emby 用户创建、更新、删除等历史快照
    - 保存 `UserDto` JSON 快照与密码哈希

    输入参数:
    - 无 (ORM 实例化时传入字段)

    返回值:
    - 无
    """

    __tablename__ = "emby_user_history"

    id: Mapped[auto_int_pk]

    emby_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="Emby 用户ID(字符串)")

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="Emby 用户名")

    user_dto: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="UserDto JSON 快照")

    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="密码哈希 (bcrypt)")

    action: Mapped[str] = mapped_column(String(32), nullable=False, comment="动作类型(create/update/delete)")

    __table_args__ = (Index("idx_emby_user_history_user_action", "emby_user_id", "action"),)

    repr_cols = ("id", "emby_user_id", "action", "created_at")
