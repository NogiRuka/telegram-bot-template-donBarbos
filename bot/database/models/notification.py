from __future__ import annotations
from typing import Any

from sqlalchemy import String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class NotificationModel(Base, BasicAuditMixin):
    """Emby 通知队列表
    
    功能说明:
    - 存储来自 Webhook 的原始通知事件 (如 library.new)
    - 记录通知处理状态
    
    字段:
    - type: 通知类型 (library.new 等)
    - status: 状态 
        - pending_completion: 待补全 (已收到 Webhook, 仅有基本ID)
        - pending_review: 待审核 (已从 Emby API 补全数据)
        - sent: 已发送
        - failed: 失败
    - item_id: 关联的 Emby Item ID
    - item_name: 关联的媒体名称
    - payload: 原始 Webhook JSON 数据
    - target_channel_id: 发送到的频道ID
    - target_group_id: 发送到的群组ID
    """

    __tablename__ = "emby_notifications"

    id: Mapped[auto_int_pk]

    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="通知类型")
    
    status: Mapped[str] = mapped_column(
        String(32), 
        nullable=False, 
        default="pending_completion", 
        index=True, 
        comment="状态: pending_completion/pending_review/sent/failed"
    )

    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="Emby Item ID")
    item_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="媒体名称")

    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="原始 Webhook 数据")
    
    target_channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="目标频道ID")
    target_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="目标群组ID")

    repr_cols = ("id", "type", "status", "item_name")


class EmbyItemModel(Base, BasicAuditMixin):
    """Emby 媒体详情表
    
    功能说明:
    - 存储从 Emby API 补全后的媒体详细信息
    - 用于生成通知内容
    """
    
    __tablename__ = "emby_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="Emby Item ID")
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="媒体名称")
    date_created: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="创建时间")
    overview: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简介")
    type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="类型")
    
    people: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True, comment="人员信息")
    tag_items: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True, comment="标签项")
    image_tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="图片标签")
    
    original_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始数据")

    repr_cols = ("id", "name", "type")
