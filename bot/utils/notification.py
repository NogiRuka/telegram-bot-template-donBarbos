from __future__ import annotations
from typing import TYPE_CHECKING

from bot.core.config import settings

if TYPE_CHECKING:
    from bot.database.models.emby_item import EmbyItemModel


OVERVIEW_MAX_LEN = 150


def _build_item_image_url(item: EmbyItemModel) -> str | None:
    """构造媒体封面图片URL。

    功能说明：
    - 使用 `Primary` 或 `Logo` 图片Tag构造 Emby 图片访问链接

    输入参数：
    - item: EmbyItemModel 媒体详情

    返回值：
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

    return f"{base_url.rstrip('/')}/Items/{item.id}/Images/{image_type}?tag={tag}"


def _extract_library_tag(path: str | None) -> str:
    """从媒体路径解析分类标签。

    功能说明：
    - 兼容 Windows 路径分隔符
    - 约定目录包含 "钙片/剧集/电影" 时生成对应 tag

    输入参数：
    - path: 文件路径或 None

    返回值：
    - str: 标签字符串, 不存在返回空串
    """

    if not path:
        return ""

    parts = [p for p in path.replace("\\", "/").split("/") if p]
    if "钙片" in parts:
        idx = parts.index("钙片")
        if idx + 1 < len(parts):
            return f"#{parts[idx + 1]}"
        return ""

    if "剧集" in parts:
        return "#剧集"
    if "电影" in parts:
        return "#电影"
    return ""


def _build_series_info(item: EmbyItemModel) -> str:
    """生成剧集进度与状态文本(仅 Series)。

    功能说明：
    - 仅当 item.type == "Series" 时返回内容, 否则返回空串

    输入参数：
    - item: EmbyItemModel 媒体详情

    返回值：
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

    功能说明：
    - 将简介限制在 `OVERVIEW_MAX_LEN` 以内, 超出部分追加省略号

    输入参数：
    - overview: 原始简介文本

    返回值：
    - str: 截断后的简介文本
    """

    if len(overview) > OVERVIEW_MAX_LEN:
        return overview[:OVERVIEW_MAX_LEN] + "..."
    return overview


def get_notification_content(item: EmbyItemModel) -> tuple[str, str | None]:
    """生成通知消息内容和图片URL。

    功能说明：
    - 基于 `EmbyItemModel` 生成推送文案与图片链接
    - 图片链接使用 Emby `/Items/{Id}/Images/{Type}` 接口

    输入参数：
    - item: EmbyItemModel 媒体详情

    返回值：
    - tuple[str, str | None]: (消息HTML文本, 图片URL或None)
    """

    image_url = _build_item_image_url(item)
    library_tag = _extract_library_tag(item.path)
    series_info = _build_series_info(item)

    msg_parts: list[str] = [f"🎬 <b>名称：</b><code>{item.name}</code>"]
    if library_tag:
        msg_parts.append(f"📂 <b>分类：</b>{library_tag}")
    if series_info:
        msg_parts.append(series_info)

    msg_parts.append(f"📅 <b>时间：</b>{item.date_created if item.date_created else '未知'}")

    overview = item.overview or ""
    if overview:
        msg_parts.append(f"📝 <b>简介：</b>{_truncate_overview(overview)}")

    return "\n".join(msg_parts), image_url
