from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from bot.core.constants import EVENT_TYPE_LIBRARY_NEW, NOTIFICATION_STATUS_PENDING_REVIEW
from bot.database.models.emby_item import EmbyItemModel
from bot.database.models.notification import NotificationModel
from bot.services.notification.utils import business_key

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.selectable import Subquery


class NotificationQueryService:
    @staticmethod
    def preview_subquery() -> Subquery:
        """构造预览子查询(按业务Key去重, 取最小通知ID)。

        功能说明:
        - 对 `pending_review` + `library.new` 的通知按业务Key分组去重
        - 每组取 `min(notification.id)` 作为代表记录

        输入参数:
        - 无

        返回值:
        - sqlalchemy.sql.selectable.Subquery: 预览子查询
        """

        bk = business_key()
        return (
            select(
                func.min(NotificationModel.id).label("notif_id"),
                bk.label("biz_id"),
            )
            .where(
                NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
                NotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
            )
            .group_by(bk)
            .subquery()
        )

    @staticmethod
    async def get_preview_rows(session: AsyncSession) -> list[tuple[NotificationModel, EmbyItemModel]]:
        """获取预览所需的通知与媒体详情行。

        功能说明:
        - 按业务Key去重后返回 (NotificationModel, EmbyItemModel) 元组列表

        输入参数:
        - session: AsyncSession 数据库会话

        返回值:
        - list[tuple[NotificationModel, EmbyItemModel]]: 预览行列表
        """

        subq = NotificationQueryService.preview_subquery()

        stmt = (
            select(NotificationModel, EmbyItemModel)
            .join(subq, NotificationModel.id == subq.c.notif_id)
            .join(EmbyItemModel, EmbyItemModel.id == subq.c.biz_id)
        )

        result = await session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    @staticmethod
    async def count_by_status(session: AsyncSession, statuses: list[str]) -> dict[str, int]:
        """按状态统计通知数量(基于业务Key去重)。

        功能说明:
        - 只统计 `library.new` 类型
        - 通过 `distinct(business_key)` 保证 Episode 同剧集只计一次

        输入参数:
        - session: AsyncSession 数据库会话
        - statuses: 需要统计的状态列表

        返回值:
        - dict[str, int]: {status: count} 映射
        """

        bk = business_key()
        stmt = (
            select(
                NotificationModel.status,
                func.count(func.distinct(bk)).label("cnt"),
            )
            .where(
                NotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
                NotificationModel.status.in_(statuses),
            )
            .group_by(NotificationModel.status)
        )
        rows = await session.execute(stmt)
        return {row.status: row.cnt for row in rows}
