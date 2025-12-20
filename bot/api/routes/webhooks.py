"""
Webhooks 路由
处理来自 Emby 的 Webhook 回调请求
"""

from __future__ import annotations
import json
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.core.config import settings
from bot.core.loader import bot
from bot.database.database import sessionmaker
from bot.database.models.notification import NotificationModel

try:
    import orjson
except Exception:
    orjson = None  # type: ignore
from loguru import logger

router = APIRouter()


@router.post("/webhooks/emby")
async def handle_emby_webhook(
    request: Request,
    x_emby_event: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """
    处理 Emby Webhook 回调

    功能说明:
    - 接收 Emby Webhooks 插件发送的事件回调 (POST JSON)
    - 所有事件类型都存入数据库，状态为 pending_completion
    - 针对 library.new 事件，保持原有的特殊处理逻辑

    输入参数:
    - request: FastAPI 的请求对象, 用于读取原始 JSON 载荷
    - x_emby_event: 请求头 `X-Emby-Event` (可选), 某些配置会附带事件名

    返回值:
    - dict: 处理结果
    """

    # 读取 JSON 载荷
    try:
        payload: dict[str, Any] = await request.json()
    except (ValueError, UnicodeDecodeError) as err:
        logger.exception("❌ 解析 Emby Webhook JSON 失败")
        raise HTTPException(status_code=400, detail="Invalid JSON body") from err

    # 提取事件类型
    event_type = payload.get("Event") or x_emby_event
    
    # 提取 Item 信息（如果存在）
    item = payload.get("Item", {})
    item_id = item.get("Id")
    item_name = item.get("Name")
    item_type = item.get("Type")
    
    # 提取剧集相关信息
    series_id = item.get("SeriesId")
    series_name = item.get("SeriesName")
    season_number = item.get("ParentIndexNumber")
    episode_number = item.get("IndexNumber")
    
    # 所有事件都存入数据库
    if event_type:
        logger.info(f"📥 收到 Emby Webhook 事件: {event_type}")
        
        # 存入数据库 (状态为 pending_completion)
        async with sessionmaker() as session:
            notification = NotificationModel(
                type=event_type,
                status="pending_completion",
                item_id=item_id,
                item_name=item_name,
                item_type=item_type,
                series_id=series_id,
                season_id=season_id,
                series_name=series_name,
                season_number=season_number,
                episode_number=episode_number,
                payload=payload
            )
            session.add(notification)
            await session.commit()
            await session.refresh(notification)
            
            # 剧集信息显示
            if series_name and season_number and episode_number:
                logger.info(f"💾 通知已存入数据库, 状态待补全, ID: {notification.id}, 事件类型: {event_type}, 媒体类型: {item_type}, 剧集: {series_name} 第{season_number}季第{episode_number}集, Item: {item_name} ({item_id})")
            else:
                logger.info(f"💾 通知已存入数据库, 状态待补全, ID: {notification.id}, 事件类型: {event_type}, 媒体类型: {item_type}, Item: {item_name} ({item_id})")
            
        # 针对 library.new 事件的特殊处理（保持原有逻辑）
        if event_type == "library.new":
            logger.info("🆕 收到新媒体入库通知 (library.new)")
            if not item_id:
                logger.warning("⚠️ Webhook 载荷中缺少 Item.Id")
    else:
        logger.warning("⚠️ Webhook 载荷中缺少事件类型")

    pretty = format_json_pretty(payload)
    logger.debug("📥 Emby Webhook 详细载荷:\n{}", pretty)

    return {
        "status": "ok",
        "x_emby_event": x_emby_event,
        "processed": bool(event_type)  # 只要有事件类型就认为是已处理
    }


def format_json_pretty(data: Any) -> str:
    """将对象美化为 JSON 字符串

    功能说明：
    - 优先使用 `orjson` 进行缩进美化并保持非 ASCII 字符
    - 兼容回退到标准库 `json.dumps`，`ensure_ascii=False` 防止中文被转义

    输入参数：
    - data: 任意可序列化对象（通常为 dict / list）

    返回值：
    - str: 缩进美化后的 JSON 字符串

    依赖安装方式：
    - `pip install orjson`（已在项目依赖中声明）
    """
    try:
        if orjson is not None:
            return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        try:
            return json.dumps({"unserializable": str(type(data))}, ensure_ascii=False)
        except Exception:
            return "{}"
