"""HTTP endpoints for the Emby metadata workbench."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from bot.database.database import sessionmaker
from bot.database.models import LibraryNewNotificationModel
from bot.services.emby_metadata.models import MetadataCandidate
from bot.services.emby_metadata.sources.ck_download import CkDownloadSource
from bot.services.emby_metadata.writer import apply_metadata_candidate_to_item

router = APIRouter(prefix="/emby/metadata")

_search_cache: dict[str, list[dict[str, Any]]] = {}


class SearchRequest(BaseModel):
    """The selected notifications to look up."""

    notification_ids: list[str] = Field(min_length=1, max_length=30)


class WritebackRequest(BaseModel):
    """A user-confirmed metadata writeback operation."""

    candidate: MetadataCandidate
    fields: list[str] = Field(default_factory=list)
    overwrite: bool = False
    confirmed: bool = False


def _path_from_payload(notification: LibraryNewNotificationModel) -> str:
    """Extract the Emby path without requiring an exact webhook payload shape."""
    item = notification.payload.get("Item", {}) if notification.payload else {}
    return str(item.get("Path") or notification.payload.get("Path") or "")


def _queue_item(notification: LibraryNewNotificationModel) -> dict[str, Any]:
    """Turn a persisted library notification into the frontend queue shape."""
    path = _path_from_payload(notification)
    category = "japanese_korean" if "日语" in path or "动漫" in path else "domestic"
    return {
        "notification_id": str(notification.id),
        "item_id": notification.item_id or "",
        "item_name": notification.item_name or notification.title or "未命名条目",
        "path": path,
        "category": category,
        "category_label": "日语动漫" if category == "japanese_korean" else "国产",
        "source": "ck-download" if category == "japanese_korean" else "未配置",
        "status": "pending" if notification.status == "pending_completion" else notification.status or "pending",
        "search_keyword": notification.item_name or notification.title or "",
        "search_count": len(_search_cache.get(str(notification.id), [])),
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


@router.get("/queue")
async def get_queue() -> dict[str, Any]:
    """Return movie notifications that are eligible for metadata completion."""
    async with sessionmaker() as session:
        result = await session.execute(
            select(LibraryNewNotificationModel)
            .where(LibraryNewNotificationModel.type == "library.new")
            .where(LibraryNewNotificationModel.status == "pending_completion")
            .where(LibraryNewNotificationModel.item_type == "Movie")
            .order_by(LibraryNewNotificationModel.id.desc())
        )
        notifications = [item for item in result.scalars() if "钙片" in _path_from_payload(item)]
    items = [_queue_item(notification) for notification in notifications]
    return {"items": items, "total": len(items)}


@router.post("/queue/search")
async def search_queue(request: SearchRequest) -> list[dict[str, Any]]:
    """Search selected queue entries without eagerly fetching candidate details."""
    source = CkDownloadSource()
    response: list[dict[str, Any]] = []
    for notification_id in request.notification_ids:
        notification = await _get_notification(notification_id)
        item = _queue_item(notification)
        if item["source"] != "ck-download":
            response.append({"notification_id": notification_id, "results": []})
            continue
        try:
            results = await source.search(item["search_keyword"])
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"数据源搜索失败：{error}") from error
        serialized = [result.model_dump(mode="json") for result in results]
        _search_cache[notification_id] = serialized
        response.append({"notification_id": notification_id, "results": serialized})
    return response


@router.get("/candidates/{source}/{source_id}")
async def get_candidate(source: str, source_id: str) -> dict[str, Any]:
    """Fetch one explicitly selected candidate's complete metadata."""
    if source != "ck-download":
        raise HTTPException(status_code=404, detail="不支持的数据源")
    try:
        candidate = await CkDownloadSource().fetch_detail(source_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"候选详情抓取失败：{error}") from error
    return candidate.model_dump(mode="json")


@router.post("/queue/{notification_id}/writeback")
async def writeback(notification_id: str, request: WritebackRequest) -> dict[str, Any]:
    """Write a confirmed candidate to Emby and mark the notification complete."""
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="写入操作需要明确确认")
    notification = await _get_notification(notification_id)
    if not notification.item_id:
        raise HTTPException(status_code=400, detail="队列项目缺少 Emby Item ID")
    try:
        result = await apply_metadata_candidate_to_item(notification.item_id, request.candidate)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Emby 写入失败：{error}") from error
    async with sessionmaker() as session:
        stored = await session.get(LibraryNewNotificationModel, notification.id)
        if stored is not None:
            stored.status = "written"
            await session.commit()
    return {"ok": True, "result": result}
