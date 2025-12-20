from __future__ import annotations
from typing import Any

from sqlalchemy import case

from bot.database.models.notification import NotificationModel


def business_key() -> Any:
    """构造用于通知去重/分组的业务Key表达式.

    功能说明:
    - Episode 类型按 `series_id` 作为业务实体(同一剧集多集视为一条业务记录)
    - 其他类型按 `item_id` 作为业务实体

    输入参数:
    - 无

    返回值:
    - Any: SQLAlchemy 表达式, 可用于 `group_by`/`distinct`
    """

    return case(
        (
            (NotificationModel.item_type == "Episode") & (NotificationModel.series_id.isnot(None)),
            NotificationModel.series_id,
        ),
        else_=NotificationModel.item_id,
    )
