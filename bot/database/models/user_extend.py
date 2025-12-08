"""
用户扩展信息模型

包含权限角色、电话、简介、多IP、最后交互时间等扩展字段。
"""

from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, big_int_pk
from datetime import datetime as dt


class UserRole(Enum):
    """用户角色枚举"""

    user = "user"
    admin = "admin"
    owner = "owner"


class UserExtendModel(Base, BasicAuditMixin):
    """用户扩展信息模型

    功能说明:
    - 存储不属于 aiogram User 的扩展信息与权限，如角色、电话、简介、IP 列表、最后交互时间

    字段:
    - user_id: 用户ID（主键，逻辑关联 users.id，无物理外键约束）
    - role: 用户角色权限（user/admin/owner），默认 user
    - phone: 电话号码（可空）
    - bio: 简介（可空）
    - ip_list: 访问过的 IP 数组(JSON)
    - last_interaction_at: 最后与机器人交互的时间
    - remark: 备注
    - 审计字段: created_at/updated_at/is_deleted/deleted_at/created_by/updated_by/deleted_by

    返回值:
    - 无
    """

    __tablename__ = "user_extend"

    # 用户 ID (逻辑关联，不设外键)
    user_id: Mapped[big_int_pk] = mapped_column(comment="用户 ID (逻辑关联 users.id)")

    # 角色权限
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole"), default=UserRole.user, nullable=False, index=True, comment="用户角色权限"
    )

    # 电话与简介
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="电话号码(可空)")
    bio: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="用户简介(可空)")

    # Emby 用户ID(字符串)
    emby_user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="Emby 用户ID(字符串)"
    )

    # IP 列表与最后交互时间
    ip_list: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True, comment="访问过的IP数组")
    last_interaction_at: Mapped[dt | None] = mapped_column(
        nullable=True,
        comment="最后与机器人交互的时间",
    )

    __table_args__ = (
        Index("idx_user_extend_role", "role"),
        Index("idx_user_extend_last_interaction", "last_interaction_at"),
    )
