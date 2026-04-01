from __future__ import annotations

from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class EmbyDeviceHistoryModel(Base, BasicAuditMixin):
    """Emby 设备历史模型。

    用于记录设备的创建、更新、删除、恢复等变更明细。
    """

    __tablename__ = "emby_device_history"

    id: Mapped[auto_int_pk]

    emby_device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="Emby 设备ID")
    device_pk: Mapped[int | None] = mapped_column(nullable=True, index=True, comment="设备主表ID快照")
    reported_device_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="上报设备ID快照")
    last_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="最后使用用户ID快照")
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="动作类型(create/update/delete/restore)")
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="来源(sync/user/system)")
    changed_fields: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="变更字段列表")
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更前快照")
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="变更后快照")
    diff_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="字段级差异(old/new)")

    __table_args__ = (
        Index("idx_emby_device_history_device_action", "emby_device_id", "action"),
        Index("idx_emby_device_history_device_created", "emby_device_id", "created_at"),
        Index("idx_emby_device_history_user_created", "last_user_id", "created_at"),
    )

    repr_cols = ("id", "emby_device_id", "action", "source", "created_at")
