from __future__ import annotations
from typing import Any

from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, big_int_pk


class NotificationModel(Base, BasicAuditMixin):
    """系统通知队列表

    功能说明:
    - 存储来自 Webhook 的原始通知事件 (如 library.new)
    - 用于暂存待管理员确认的消息，防止因元数据不全导致通知质量差
    - 记录通知发送状态

    字段:
    - type: 通知类型 (library.new / system / etc)
    - status: 状态 (pending / approved / sent / rejected / failed)
    - item_id: 关联的 Emby Item ID (可选)
    - item_name: 关联的媒体名称 (可选)
    - payload: 原始 Webhook JSON 数据
    """

    __tablename__ = "system_notifications"

    id: Mapped[big_int_pk]

    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="通知类型")
    
    status: Mapped[str] = mapped_column(
        String(32), 
        nullable=False, 
        default="pending", 
        index=True, 
        comment="状态: pending/approved/sent/rejected/failed"
    )

    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="Emby Item ID")
    item_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="媒体名称")

    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="原始 Webhook 数据")

    repr_cols = ("id", "type", "status", "item_name")
