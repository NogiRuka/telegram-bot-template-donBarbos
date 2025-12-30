import datetime
from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class EmbyDeviceModel(Base, BasicAuditMixin):
    """Emby 设备模型

    功能说明:
    - 存储从 Emby 同步的设备信息 (/Devices 接口)
    """
    __tablename__ = "emby_devices"

    id: Mapped[auto_int_pk]

    # Emby returns "Id" which is the internal ID (e.g., "806")
    emby_device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, comment="Emby 设备ID (Id)")

    # "ReportedDeviceId" (e.g., "7e06...")
    reported_device_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="上报设备ID (ReportedDeviceId)")

    name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="设备名称 (Name)")
    last_user_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="最后使用用户名 (LastUserName)")
    app_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="应用名称 (AppName)")
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="应用版本 (AppVersion)")
    last_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="最后用户ID (LastUserId)")

    date_last_activity: Mapped[datetime.datetime | None] = mapped_column(nullable=True, comment="最后活动时间 (DateLastActivity)")

    icon_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="图标URL (IconUrl)")
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="IP地址 (IpAddress)")

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始JSON数据")

    __table_args__ = (
        Index("idx_emby_device_last_user", "last_user_id"),
        Index("idx_emby_device_reported_id", "reported_device_id"),
    )
