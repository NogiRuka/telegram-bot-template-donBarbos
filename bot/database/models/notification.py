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
    item_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="媒体类型")

    # 剧集相关字段
    series_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="剧集ID (SeriesId)")
    series_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="剧集名称")
    season_number: Mapped[int | None] = mapped_column(nullable=True, comment="季号 (ParentIndexNumber)")
    episode_number: Mapped[int | None] = mapped_column(nullable=True, comment="集号 (IndexNumber)")
    
    target_channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="目标频道ID")
    target_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="目标群组ID")

    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="原始 Webhook 数据")

    repr_cols = ("id", "type", "status", "item_name", "series_name", "season_number", "episode_number", "item_type")

