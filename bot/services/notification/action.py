from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_PENDING_REVIEW,
    NOTIFICATION_STATUS_REJECTED,
    NOTIFICATION_STATUS_SENT,
)
from bot.database.models.notification import NotificationModel
from bot.services.notification.utils import business_key

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class NotificationActionService:
    @staticmethod
    async def reject_single_by_notification_id(
        session: AsyncSession,
        notif_id: int,
        updated_by: int | None = None,
    ) -> str | None:
        """拒绝单条通知(仅影响该记录)。

        功能说明:
        - 只拒绝指定 `notif_id` 的通知
        - 仅对 `pending_review` + `library.new` 生效

        输入参数:
        - session: AsyncSession 数据库会话
        - notif_id: 通知ID
        - updated_by: 操作者用户ID(可选)

        返回值:
        - str | None: 成功时返回通知标题(用于反馈), 否则返回 None
        """

        stmt = select(NotificationModel).where(
            NotificationModel.id == notif_id,
            NotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
            NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
        )
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()
        if not notification:
            return None

        notification.status = NOTIFICATION_STATUS_REJECTED
        if updated_by is not None:
            notification.updated_by = updated_by

        await session.commit()
        return notification.title or notification.item_name or notification.series_name

    @staticmethod
    async def mark_group_sent(
        session: AsyncSession,
        biz_id: str,
        target_channels: list[str | int],
        success: bool,
        updated_by: int | None = None,
    ) -> None:
        """按业务Key更新同一组通知的发送状态。

        功能说明:
        - 将同一业务实体(Series/Movie 或 Episode->Series)下的 `pending_review` 通知统一更新为 sent/failed
        - 发送成功时记录目标频道/群组ID列表到 `target_channel_id`

        输入参数:
        - session: AsyncSession 数据库会话
        - biz_id: 业务Key对应的ID(SeriesId 或 ItemId)
        - target_channels: 目标频道/群组ID列表
        - success: 是否至少有一个目标发送成功
        - updated_by: 操作者用户ID(可选)

        返回值:
        - None
        """

        values: dict[str, object] = {
            "status": NOTIFICATION_STATUS_SENT if success else NOTIFICATION_STATUS_FAILED,
            "target_channel_id": ",".join(str(x) for x in target_channels) if success else None,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by

        await session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
                NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
                business_key() == biz_id,
            )
            .values(**values),
        )
