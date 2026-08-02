"""Emby 元数据工作台的 HTTP 路由层。"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from bot.services.emby_metadata import workbench
from bot.services.emby_metadata.models import MetadataCandidate

router = APIRouter(prefix="/emby/metadata")


class SearchRequest(BaseModel):
    """批量搜索时由管理员选中的通知项。"""

    notification_ids: list[str] = Field(min_length=1, max_length=30)


class WritebackRequest(BaseModel):
    """已由管理员二次确认的元数据写入请求。"""

    candidate: MetadataCandidate
    fields: list[str] = Field(default_factory=list)
    overwrite: bool = False
    confirmed: bool = False


@router.get("/queue")
async def get_queue() -> dict[str, Any]:
    """获取待处理队列。"""
    return await workbench.get_queue()


@router.post("/queue/search")
async def search_queue(request: SearchRequest) -> list[dict[str, Any]]:
    """批量搜索选中项目。"""
    return await workbench.search_queue(request.notification_ids)


@router.get("/candidates/{source}/{source_id}")
async def get_candidate(source: str, source_id: str) -> dict[str, Any]:
    """获取管理员选中的候选详情。"""
    return (await workbench.get_candidate(source, source_id)).model_dump(mode="json")


@router.post("/queue/{notification_id}/writeback")
async def writeback(notification_id: str, request: WritebackRequest) -> dict[str, Any]:
    """确认后写入 Emby。"""
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="写入操作需要明确确认")
    return {"ok": True, "result": await workbench.writeback(notification_id, request.candidate)}
