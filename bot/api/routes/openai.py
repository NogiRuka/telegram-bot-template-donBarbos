"""OpenAI 管理接口路由。"""

from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any, Literal

import aiohttp
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from bot.core.config import settings
from bot.services.openai import OpenAIClient
from bot.services.openai_usage import usage_tracker
from bot.utils.http import HttpRequestError

router = APIRouter(prefix="/openai")


@router.get("/usage")
async def get_openai_usage() -> dict[str, Any]:
    """返回本地记录的 OpenAI token 用量和估算成本。"""
    return await usage_tracker.summary()


@router.get("/costs")
async def get_openai_costs(
    start_time: Annotated[
        int | None,
        Query(description="查询时间范围起点，Unix 秒，包含该时间；不传则查询最近 7 天"),
    ] = None,
    api_key_ids: Annotated[list[str] | None, Query(description="按 API Key ID 过滤")] = None,
    bucket_width: Annotated[Literal["1d"] | None, Query(description="时间桶宽度")] = "1d",
    end_time: Annotated[int | None, Query(description="查询时间范围终点，Unix 秒，不包含该时间")] = None,
    group_by: Annotated[
        list[Literal["project_id", "line_item", "api_key_id"]] | None,
        Query(description="成本分组字段，可重复传入"),
    ] = None,
    limit: Annotated[int | None, Query(ge=1, le=180, description="返回时间桶数量")] = 7,
    page: Annotated[str | None, Query(description="分页游标")] = None,
    project_ids: Annotated[list[str] | None, Query(description="按项目 ID 过滤")] = None,
) -> dict[str, Any]:
    """获取 OpenAI 组织成本数据。"""
    request_start_time = start_time if start_time is not None else int(time.time()) - 7 * 24 * 60 * 60
    if end_time is not None and end_time <= request_start_time:
        raise HTTPException(status_code=400, detail="end_time 必须大于 start_time")
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API 未配置")

    params: dict[str, Any] = {
        "start_time": request_start_time,
        "bucket_width": bucket_width,
        "limit": limit,
    }
    if end_time is not None:
        params["end_time"] = end_time
    if page:
        params["page"] = page
    if api_key_ids:
        params["api_key_ids"] = api_key_ids
    if project_ids:
        params["project_ids"] = project_ids
    if group_by:
        params["group_by"] = group_by

    client = OpenAIClient(settings.OPENAI_API_KEY, settings.OPENAI_API_BASE)
    try:
        return await client.get_costs(params)
    except HttpRequestError as error:
        logger.error("OpenAI 成本接口请求失败: status={}", error.status)
        raise HTTPException(status_code=error.status, detail="OpenAI 成本接口请求失败") from error
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        logger.error("OpenAI 成本接口网络请求失败: {}", error)
        raise HTTPException(status_code=502, detail="OpenAI 成本接口暂时不可用") from error
    except TypeError as error:
        logger.error("OpenAI 成本接口响应格式错误: {}", error)
        raise HTTPException(status_code=502, detail="OpenAI 成本接口响应格式错误") from error
    finally:
        await client.close()
