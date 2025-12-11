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
    - 针对 library.new 事件，将数据存入数据库并通知管理员确认
    - 其他事件仅做日志记录

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
    
    # 针对 library.new 事件的处理
    if event_type == "library.new":
        logger.info("🆕 收到新媒体入库通知 (library.new)")
        
        # 提取 Item 信息
        item = payload.get("Item", {})
        item_id = item.get("Id")
        item_name = item.get("Name")
        
        if item_id:
            # 1. 存入数据库 (状态为 pending)
            async with sessionmaker() as session:
                notification = NotificationModel(
                    type="library.new",
                    status="pending",
                    item_id=item_id,
                    item_name=item_name,
                    payload=payload
                )
                session.add(notification)
                await session.commit()
                await session.refresh(notification)
                
                logger.info(f"💾 通知已存入数据库, ID: {notification.id}, Item: {item_name} ({item_id})")

                # 2. 通知管理员进行确认
                admin_id = settings.OWNER_ID
                
                # 构建确认按钮
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ 立即发送", callback_data=f"notify_approve:{notification.id}"),
                        InlineKeyboardButton(text="❌ 忽略此条", callback_data=f"notify_reject:{notification.id}")
                    ]
                ])
                
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"🆕 <b>新媒体入库待确认</b>\n\n"
                            f"🎬 <b>标题:</b> {item_name}\n"
                            f"🆔 <b>ID:</b> <code>{item_id}</code>\n\n"
                            f"⚠️ 收到 Webhook 通知，但为防止元数据缺失，已暂停发送。\n"
                            f"请确认 Emby 刮削完成后，点击下方按钮发送通知。"
                        ),
                        reply_markup=kb
                    )
                    logger.info(f"📨 已向管理员 ({admin_id}) 发送确认请求")
                except Exception as e:
                    logger.error(f"❌ 发送管理员确认消息失败: {e}")
                    
        else:
            logger.warning("⚠️ Webhook 载荷中缺少 Item.Id")
            
    else:
        logger.info(f"📥 收到 Emby Webhook 事件: {event_type}")

    pretty = format_json_pretty(payload)
    logger.debug("📥 Emby Webhook 详细载荷:\n{}", pretty)

    return {
        "status": "ok",
        "x_emby_event": x_emby_event,
        "processed": event_type == "library.new"
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
