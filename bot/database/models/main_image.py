from __future__ import annotations
from typing import Any
from datetime import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class MainImageModel(Base, BasicAuditMixin):
    """主图库模型

    功能说明:
    - 存储用于主消息展示的图片条目（文件ID及元数据）

    输入参数:
    - 无（ORM 模型）

    返回值:
    - 无
    """
    __tablename__ = "main_images"

    id: Mapped[auto_int_pk]

    file_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, comment="Telegram 文件ID")
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="来源类型: photo/document")
    mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="MIME 类型")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="宽像素")
    height: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="高像素")
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="文件大小(字节)")

    is_nsfw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否 NSFW")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否参与投放")

    caption: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始说明文本")
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文件哈希（去重）")
    tags: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True, comment="标签数组")
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展信息(JSON)")

    __table_args__ = (
        Index("idx_main_images_enabled_nsfw", "is_enabled", "is_nsfw"),
        Index("idx_main_images_hash", "hash"),
    )


class MainImageScheduleModel(Base, BasicAuditMixin):
    """主图投放计划模型

    功能说明:
    - 定时在指定时间窗口内优先投放特定主图

    输入参数:
    - 无（ORM 模型）

    返回值:
    - 无
    """
    __tablename__ = "main_image_schedule"

    id: Mapped[auto_int_pk]

    image_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="关联 main_images.id")
    start_time: Mapped[dt] = mapped_column(DateTime, nullable=False, comment="开始时间(含)")
    end_time: Mapped[dt] = mapped_column(DateTime, nullable=False, comment="结束时间(含)")
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, comment="优先级(小者先)")

    only_sfw: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="仅用于 SFW 模式")
    allow_nsfw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="允许用于 NSFW 模式")

    label: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="计划标签")
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展信息(JSON)")

    __table_args__ = (
        Index("idx_image_schedule_window", "start_time", "end_time"),
        Index("idx_image_schedule_priority", "priority"),
    )

