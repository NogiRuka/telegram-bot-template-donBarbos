"""
Webhooks 路由
处理来自 Emby 的 Webhook 回调请求
"""
from __future__ import annotations
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from loguru import logger

from bot.api_server.config import settings

router = APIRouter()


@router.post("/webhooks/emby")
async def handle_emby_webhook(
    request: Request,
    x_emby_event: Annotated[str | None, Header()] = None,
    x_webhook_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """
    处理 Emby Webhook 回调

    功能说明:
    - 接收 Emby Webhooks 插件发送的事件回调 (POST JSON)
    - 支持通过 Header `X-Webhook-Token` 或查询参数 `token` 进行简单鉴权
    - 尽量兼容不同事件载荷结构, 进行日志记录与基本回执

    输入参数:
    - request: FastAPI 的请求对象, 用于读取原始 JSON 载荷
    - x_emby_event: 请求头 `X-Emby-Event` (可选), 某些配置会附带事件名
    - x_webhook_token: 请求头 `X-Webhook-Token` (可选), 用于鉴权
    - token: 查询参数 `token` (可选), 用于鉴权

    返回值:
    - dict: 处理结果, 包含状态与解析的关键信息
    """
    # 简单鉴权: 如果配置了 EMBY_WEBHOOK_TOKEN, 则要求 Header 或查询参数匹配
    expected_token = getattr(settings, "EMBY_WEBHOOK_TOKEN", None)
    provided_token = x_webhook_token or token

    if expected_token and (not provided_token or provided_token != expected_token):
        logger.warning("拒绝 Emby Webhook: 令牌不匹配或缺失")
        raise HTTPException(status_code=401, detail="Unauthorized webhook")

    # 读取 JSON 载荷
    try:
        payload: dict[str, Any] = await request.json()
    except (ValueError, UnicodeDecodeError) as err:
        logger.exception("解析 Emby Webhook JSON 失败")
        raise HTTPException(status_code=400, detail="Invalid JSON body") from err

    # 尝试从载荷中提取常见字段 (尽量兼容不同插件版本)
    event_name = (
        (payload.get("Event") or payload.get("event") or payload.get("NotificationType"))
        or x_emby_event
        or "unknown"
    )
    item = payload.get("Item") or payload.get("item") or {}
    user = payload.get("User") or payload.get("user") or {}
    server = payload.get("Server") or payload.get("server") or {}
    # 可选字段: 标题、描述、时间
    title = payload.get("Title") or payload.get("title")
    description = payload.get("Description") or payload.get("description")
    event_time = payload.get("Date") or payload.get("date")

    item_name = item.get("Name") or item.get("name")
    item_id = item.get("Id") or item.get("id")
    item_type = item.get("Type") or item.get("type")
    user_name = user.get("Name") or user.get("name")
    user_id = user.get("Id") or user.get("id")

    # 记录日志, 便于后续观测与调试
    logger.info(
        "收到 Emby Webhook: event={}, title={}, item=({}:{}, {}), user=({}:{})",
        event_name,
        title,
        item_name,
        item_id,
        item_type,
        user_name,
        user_id,
    )

    # 这里可以根据不同事件进行业务处理, 例如:
    # - PlaybackStart / PlaybackStop: 统计观看记录
    # - ItemAdded: 同步媒资到数据库
    # - UserDeleted: 清理相关数据
    # 为了安全示范, 本模板仅做日志记录与回执; 可根据需求接入 bot.services 中的业务逻辑

    return {
        "status": "ok",
        "event": event_name,
        "title": title,
        "description": description,
        "date": event_time,
        "item": {
            "id": item_id,
            "name": item_name,
            "type": item_type,
        },
        "user": {
            "id": user_id,
            "name": user_name,
        },
        "server": server,
    }
