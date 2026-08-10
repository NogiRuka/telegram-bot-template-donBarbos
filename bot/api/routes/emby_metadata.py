"""Emby 元数据工作台的 HTTP 路由层。"""

from typing import Any

import aiohttp
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from bot.services.emby_metadata import workbench
from bot.services.emby_metadata.models import MetadataCandidate
from bot.services.emby_metadata.translation import translate_to_chinese

router = APIRouter(prefix="/emby/metadata")


class QueueSearchSelection(BaseModel):
    """一次批量搜索中某个队列项目的搜索与路由选择。"""

    notification_id: str
    keyword: str = ""
    category: str
    source: str


class SearchRequest(BaseModel):
    """批量搜索时由管理员选中的通知项。"""

    selections: list[QueueSearchSelection] = Field(min_length=1, max_length=30)


class WritebackRequest(BaseModel):
    """已由管理员二次确认的元数据写入请求。"""

    candidate: MetadataCandidate
    fields: list[str] = Field(default_factory=list)
    overwrite: bool = False
    confirmed: bool = False


class TranslationRequest(BaseModel):
    """简介翻译请求。"""

    text: str = Field(min_length=1, max_length=20000)


@router.get("/queue")
async def get_queue() -> dict[str, Any]:
    """获取待处理队列。"""
    return await workbench.get_queue()


@router.post("/translate")
async def translate_metadata(request: TranslationRequest) -> dict[str, str]:
    """将简介翻译成中文。"""
    try:
        return {"translation": await translate_to_chinese(request.text)}
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except aiohttp.ClientError as error:
        raise HTTPException(status_code=502, detail="xAI 翻译服务暂时不可用") from error


@router.post("/queue/search")
async def search_queue(request: SearchRequest) -> list[dict[str, Any]]:
    """批量搜索选中项目。"""
    return await workbench.search_queue([item.model_dump() for item in request.selections])


@router.get("/candidates/{source}/{source_id}")
async def get_candidate(source: str, source_id: str) -> dict[str, Any]:
    """获取管理员选中的候选详情。"""
    return (await workbench.get_candidate(source, source_id)).model_dump(mode="json")


@router.get("/queue/{notification_id}/candidates/{source}/{source_id}")
async def get_candidate_preview(
    notification_id: str,
    source: str,
    source_id: str,
) -> dict[str, Any]:
    """获取候选详情及当前 Emby 字段，用于工作台对比。"""
    return await workbench.get_candidate_preview(notification_id, source, source_id)


@router.get("/images")
async def proxy_source_image(url: str, referer: str | None = None) -> Response:
    """使用数据源所需请求头代理候选图片。"""
    image_data, content_type = await workbench.proxy_source_image(url, referer)
    return Response(content=image_data, media_type=content_type)


@router.post("/queue/{notification_id}/writeback")
async def writeback(notification_id: str, request: WritebackRequest) -> dict[str, Any]:
    """确认后写入 Emby。"""
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="写入操作需要明确确认")
    return {
        "ok": True,
        "result": await workbench.writeback(
            notification_id,
            request.candidate,
            fields=request.fields,
            overwrite=request.overwrite,
        ),
    }
