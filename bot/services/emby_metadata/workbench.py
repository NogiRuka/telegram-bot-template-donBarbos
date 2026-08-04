"""Emby 元数据工作台的队列查询、候选搜索和写入编排。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select

from bot.database.database import sessionmaker
from bot.database.models import LibraryNewNotificationModel
from bot.services.emby_metadata.models import MetadataCandidate
from bot.services.emby_metadata.matching import extract_product_number
from bot.services.emby_metadata.sources.ck_download import CkDownloadSource
from bot.services.emby_metadata.writer import apply_metadata_candidate_to_item


_search_cache: dict[str, list[dict[str, Any]]] = {}


def _path_from_payload(notification: LibraryNewNotificationModel) -> str:
    """兼容不同 Webhook 载荷结构，提取 Emby 媒体路径。"""
    item = notification.payload.get("Item", {}) if notification.payload else {}
    return str(item.get("Path") or notification.payload.get("Path") or "")


def _queue_item(notification: LibraryNewNotificationModel) -> dict[str, Any]:
    """把新媒体通知转换为前端队列的数据结构。"""
    path = _path_from_payload(notification)
    payload_item = notification.payload.get("Item", {}) if notification.payload else {}
    if "日韩" in path:
        category = "japanese_korean"
        category_label = "日韩"
        source = "ck-download"
    elif "欧美" in path:  # 假设路径中包含“欧美”字样则为欧美分类
        category = "western"
        category_label = "欧美"
        source = "未配置"
    else:
        category = "domestic"
        category_label = "国产"
        source = "未配置"

    item_name = notification.item_name or notification.title or "未命名条目"
    search_keyword = extract_product_number(item_name) or item_name
    return {
        "notification_id": str(notification.id),
        "item_id": notification.item_id or "",
        "item_name": item_name,
        "path": path,
        "category": category,
        "category_label": category_label,
        "source": source,
        "status": "pending" if notification.status == "pending_completion" else notification.status or "pending",
        "search_keyword": search_keyword,
        "search_count": len(_search_cache.get(str(notification.id), [])),
        "image_url": payload_item.get("ImageUrl") or payload_item.get("PrimaryImageUrl"),
    }


async def _get_notification(notification_id: str) -> LibraryNewNotificationModel:
    try:
        primary_key = int(notification_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="队列项目不存在") from error
    async with sessionmaker() as session:
        notification = await session.get(LibraryNewNotificationModel, primary_key)
        if notification is None:
            raise HTTPException(status_code=404, detail="队列项目不存在")
        return notification


async def get_queue() -> dict[str, Any]:
    """返回符合元数据补全条件的电影通知队列。"""
    async with sessionmaker() as session:
        result = await session.execute(
            select(LibraryNewNotificationModel)
            .where(LibraryNewNotificationModel.status == "pending_completion")
            .where(LibraryNewNotificationModel.item_type == "Movie")
            .order_by(LibraryNewNotificationModel.id.desc())
        )
        notifications = list(result.scalars())
    items = [_queue_item(notification) for notification in notifications]
    return {"items": items, "total": len(items)}


async def search_queue(notification_ids: list[str], keywords: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """搜索选中项目，缓存轻量候选结果供本次工作台会话使用。"""
    source = CkDownloadSource()
    response: list[dict[str, Any]] = []
    for notification_id in notification_ids:
        item = _queue_item(await _get_notification(notification_id))
        if item["source"] != "ck-download":
            response.append({"notification_id": notification_id, "results": []})
            continue
        try:
            results = await source.search((keywords or {}).get(notification_id) or item["search_keyword"])
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"数据源搜索失败：{error}") from error
        serialized = [result.model_dump(mode="json") for result in results]
        _search_cache[notification_id] = serialized
        response.append({"notification_id": notification_id, "results": serialized})
    return response


async def get_candidate(source: str, source_id: str) -> MetadataCandidate:
    """按来源和来源 ID 获取用户明确选择的候选详情。"""
    if source != "ck-download":
        raise HTTPException(status_code=404, detail="不支持的数据源")
    try:
        return await CkDownloadSource().fetch_detail(source_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"候选详情抓取失败：{error}") from error


async def writeback(notification_id: str, candidate: MetadataCandidate) -> dict[str, Any]:
    """将候选数据写入 Emby 通知状态不改变。"""
    notification = await _get_notification(notification_id)
    if not notification.item_id:
        raise HTTPException(status_code=400, detail="队列项目缺少 Emby Item ID")
    try:
        result = await apply_metadata_candidate_to_item(notification.item_id, candidate)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Emby 写入失败：{error}") from error
    return result or {}
