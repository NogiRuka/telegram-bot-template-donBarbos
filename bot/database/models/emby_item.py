from __future__ import annotations
from typing import Any

from sqlalchemy import String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class EmbyItemModel(Base, BasicAuditMixin):
    """Emby 媒体详情表
    
    功能说明:
    - 存储从 Emby API 补全后的媒体详细信息
    - 用于生成通知内容
    """
    
    __tablename__ = "emby_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="Emby Item ID")
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="媒体名称")
    type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="类型")
    
    # 状态字段 (主要用于Series类型)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="状态 (Continuing, Ended等，仅Series类型有效)")
    # 剧集进度字段 (仅Series类型有效)
    current_season: Mapped[int | None] = mapped_column(nullable=True, comment="当前季 (仅Series类型有效)")
    current_episode: Mapped[int | None] = mapped_column(nullable=True, comment="当前集 (仅Series类型有效)")

    date_created: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="创建时间")
    overview: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简介")

    path: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="文件路径")
    people: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True, comment="人员信息")
    tag_items: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True, comment="标签项")
    image_tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="图片标签")
    
    original_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始数据")
    episode_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="剧集详情数据(JSON格式，包含所有剧集信息)")

    repr_cols = ("id", "name", "type", "status", "current_season", "current_episode")
