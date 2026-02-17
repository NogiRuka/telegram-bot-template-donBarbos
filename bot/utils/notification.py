from __future__ import annotations
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import case, func, select

from bot.core.config import settings
from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    NOTIFICATION_STATUS_PENDING_COMPLETION,
    NOTIFICATION_STATUS_PENDING_REVIEW,
    NOTIFICATION_STATUS_REJECTED,
)
from bot.database.seed_media_categories import get_enabled_categories

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.database.models.emby_item import EmbyItemModel

from bot.database.models.library_new_notification import LibraryNewNotificationModel

if TYPE_CHECKING:
    from bot.database.models.notification import NotificationModel as NotificationModelType

OVERVIEW_MAX_LEN = 150


def _build_item_image_url(item: EmbyItemModel) -> str | None:
    """构造媒体封面图片URL。

    功能说明:
    - 使用 `Primary` 或 `Logo` 图片Tag构造 Emby 图片访问链接

    输入参数:
    - item: EmbyItemModel 媒体详情

    返回值:
    - str | None: 图片URL, 无可用图片时返回 None
    """

    if not item.image_tags:
        return None

    tag = None
    image_type = None
    if "Primary" in item.image_tags:
        tag = item.image_tags["Primary"]
        image_type = "Primary"
    elif "Logo" in item.image_tags:
        tag = item.image_tags["Logo"]
        image_type = "Logo"

    if not (tag and image_type):
        return None

    base_url = settings.get_emby_base_url()
    if not base_url:
        return None

    url = f"{base_url.rstrip('/')}/Items/{item.id}/Images/{image_type}?tag={tag}"

    # 拼接 API Key 以允许 Telegram 服务器访问图片（绕过登录）
    if settings.EMBY_API_KEY:
        url += f"&api_key={settings.EMBY_API_KEY}"

    logger.info(f"生产图片 URL: {url}")
    return url


async def _extract_library_tag(path: str | None, session: AsyncSession | None = None) -> str:
    """从媒体路径解析分类标签。

    功能说明:
    - 兼容 Windows 路径分隔符
    - 从媒体库分类数据表获取分类列表
    - 约定目录包含 "钙片/剧集/电影" 时生成对应 tag
    - 路径包含 "钙片/其他" 时返回 "国产"

    输入参数:
    - path: 文件路径或 None
    - session: 异步数据库会话（可选，用于获取分类数据）

    返回值:
    - str: 标签字符串, 不存在返回空串
    """

    if not path:
        return ""

    parts = [p for p in path.replace("\\", "/").split("/") if p]

    # 从数据表获取启用的分类列表
    media_categories = []
    if session:
        try:
            media_categories = await get_enabled_categories(session)
        except Exception:
            # 数据库获取失败时使用默认值
            media_categories = ["剧集", "电影", "动漫", "国产", "日韩", "欧美"]
    else:
        # 没有session时使用默认值
        media_categories = ["剧集", "电影", "动漫", "国产", "日韩", "欧美"]

    # 特殊处理：钙片/其他 -> 国产
    if "钙片" in parts:
        idx = parts.index("钙片")
        if idx + 1 < len(parts):
            next_part = parts[idx + 1]
            if next_part == "其他":
                return "#国产"
            return f"#{next_part}"
        return ""

    # 检查路径中是否包含数据表的分类
    for category in media_categories:
        if category in parts:
            return f"#{category}"

    # 向后兼容：检查传统分类
    if "剧集" in parts:
        return "#剧集"
    if "电影" in parts:
        return "#电影"

    return ""


def _build_series_info(item: EmbyItemModel) -> str:
    """生成剧集进度与状态文本(仅 Series)。

    功能说明:
    - 仅当 item.type == "Series" 时返回内容, 否则返回空串

    输入参数:
    - item: EmbyItemModel 媒体详情

    返回值:
    - str: 剧集信息文本, 可能为空串
    """

    if item.type != "Series":
        return ""

    parts: list[str] = []
    if item.current_season and item.current_episode:
        parts.append(f"📺 <b>进度：</b>第{item.current_season}季 · 第{item.current_episode}集")

    if item.status:
        status_text = item.status
        if item.status == "Continuing":
            status_text = "更新中"
        elif item.status == "Ended":
            status_text = "已完结"
        parts.append(f"📊 <b>状态：</b>{status_text}")

    return "\n".join(parts)


def _truncate_overview(overview: str) -> str:
    """截断简介文本.

    功能说明:
    - 将简介限制在 `OVERVIEW_MAX_LEN` 以内, 超出部分追加省略号

    输入参数:
    - overview: 原始简介文本

    返回值:
    - str: 截断后的简介文本
    """

    if len(overview) > OVERVIEW_MAX_LEN:
        return overview[:OVERVIEW_MAX_LEN] + "..."
    return overview


async def get_notification_content(item: EmbyItemModel, session: AsyncSession | None = None) -> tuple[str, str | None]:
    """生成通知消息内容和图片URL。

    功能说明:
    - 基于 `EmbyItemModel` 生成推送文案与图片链接
    - 图片链接使用 Emby `/Items/{Id}/Images/{Type}` 接口
    - 支持从数据库获取媒体库分类设置

    输入参数:
    - item: EmbyItemModel 媒体详情
    - session: 异步数据库会话（可选，用于获取数据库配置）

    返回值:
    - tuple[str, str | None]: (消息HTML文本, 图片URL或None)
    """

    image_url = _build_item_image_url(item)
    library_tag = await _extract_library_tag(item.path, session)
    series_info = _build_series_info(item)

    msg_parts: list[str] = [f"🎬 <b>名称：</b><code>{item.name}</code>"]
    if library_tag:
        msg_parts.append(f"📂 <b>分类：</b>{library_tag}")
    if series_info:
        msg_parts.append(series_info)

    msg_parts.append(f"📅 <b>时间：</b>{item.date_created if item.date_created else '未知'}")

    overview = item.overview or ""
    if overview:
        # 如果包含分隔符，只取前面的内容
        if "---" in overview:
            overview = overview.split("---")[0].strip()

        if overview:
            msg_parts.append(f"📝 <b>简介：</b>{_truncate_overview(overview)}")

    return "\n".join(msg_parts), image_url


async def get_notification_status_counts(session: AsyncSession) -> tuple[int, int, int]:
    """获取通知状态统计(待补全、待审核、已拒绝)。

    功能说明:
    - 统计新片通知中不同状态的数量
    - 使用 case 语句对 Episode 和 Series 类型进行分组统计
    - Episode 类型且有 series_id 的按 series_id 分组, Series 类型按 item_id 分组
    - 现在统计的是 library_new 表的数据

    输入参数:
    - session: AsyncSession 数据库会话

    返回值:
    - tuple[int, int, int]: (待补全数量, 待审核数量, 已拒绝数量)
    """
    count_key = case(
        (
            (LibraryNewNotificationModel.item_type == "Episode")
            & (LibraryNewNotificationModel.series_id.isnot(None)),
            LibraryNewNotificationModel.series_id,
        ),
        (
            LibraryNewNotificationModel.item_type == "Series",
            LibraryNewNotificationModel.item_id,
        ),
        else_=LibraryNewNotificationModel.item_id,
    )
    stmt = (
        select(
            LibraryNewNotificationModel.status,
            func.count(func.distinct(count_key)).label("cnt"),
        )
        .where(
            LibraryNewNotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
            LibraryNewNotificationModel.status.in_([
                NOTIFICATION_STATUS_PENDING_COMPLETION,
                NOTIFICATION_STATUS_PENDING_REVIEW,
                NOTIFICATION_STATUS_REJECTED,
            ]),
        )
        .group_by(LibraryNewNotificationModel.status)
    )
    rows = await session.execute(stmt)
    counts = {row.status: row.cnt for row in rows}

    pending_completion = counts.get(NOTIFICATION_STATUS_PENDING_COMPLETION, 0)
    pending_review = counts.get(NOTIFICATION_STATUS_PENDING_REVIEW, 0)
    rejected = counts.get(NOTIFICATION_STATUS_REJECTED, 0)

    return pending_completion, pending_review, rejected


def get_check_id_for_notification(notif: NotificationModelType) -> str:
    """根据通知类型获取用于检测的ID。

    功能说明:
    - 对于Episode类型使用series_id，其他类型使用item_id

    输入参数:
    - notif: NotificationModel 通知模型

    返回值:
    - str: 用于检测的ID
    """
    if notif.item_type == "Episode" and notif.series_id:
        return notif.series_id
    return notif.item_id


def get_item_ids_from_notifications(notifications: list[NotificationModelType]) -> list[str]:
    """从通知列表中提取需要去查询的item_id列表。

    功能说明:
    - 对于Episode类型使用series_id，其他类型使用item_id，并去重

    输入参数:
    - notifications: list[NotificationModel] 通知列表

    返回值:
    - list[str]: 去重后的item_id列表
    """
    item_ids = []
    for notif in notifications:
        check_id = get_check_id_for_notification(notif)
        if check_id:
            item_ids.append(check_id)

    # 去重
    return list(set(item_ids))
