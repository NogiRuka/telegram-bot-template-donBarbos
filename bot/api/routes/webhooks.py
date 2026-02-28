"""
Webhooks 路由
处理来自 Emby 的 Webhook 回调请求
"""

from __future__ import annotations
import json
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from bot.config.constants import CONFIG_KEY_EMBY_WHITELIST_USER_IDS
from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    EVENT_TYPE_PLAYBACK_START,
)
from bot.database.database import sessionmaker
from bot.database.models.emby_user import EmbyUserModel
from bot.database.models.library_new_notification import LibraryNewNotificationModel
from bot.database.models.notification import NotificationModel
from bot.services.config_service import get_config
from bot.utils.datetime import format_datetime, now, parse_formatted_datetime
from bot.utils.emby import get_emby_client

try:
    import orjson
except Exception:
    orjson = None
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
    - 所有事件都存入数据库，但只有 library.new 事件设置状态
    - library.new 事件状态设置为 pending_completion
    - 其他事件状态字段为 None（不设置状态）
    - 为所有事件提供详细的日志记录

    输入参数:
    - request: FastAPI 的请求对象, 用于读取原始 JSON 载荷
    - x_emby_event: 请求头 `X-Emby-Event` (可选), 某些配置会附带事件名

    返回值:
    - dict: 处理结果，包含状态和已处理的事件信息

    依赖安装方式:
    - `pip install orjson` (已在项目依赖中声明)
    """

    # 读取 JSON 载荷
    try:
        payload: dict[str, Any] = await request.json()
    except (ValueError, UnicodeDecodeError) as err:
        logger.exception("❌ 解析 Emby Webhook JSON 失败")
        raise HTTPException(status_code=400, detail="Invalid JSON body") from err

    # 提取事件类型
    event_title = payload.get("Title")
    event_type = payload.get("Event")

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

    # 所有事件都存入数据库，但只有 library.new 事件设置状态
    if event_type:
        logger.info(f"📥 收到 Emby Webhook 事件: {event_type}")

        # 根据事件类型决定是否设置状态
        event_status = None  # 默认不设置状态

        # 只有 library.new 事件设置状态
        if event_type == EVENT_TYPE_LIBRARY_NEW:
            event_status = "pending_completion"
            logger.info("🆕 收到新媒体入库通知")

        # 处理网页端播放警告
        if event_type == EVENT_TYPE_PLAYBACK_START:
            await _process_playback_start(payload)

        # 存入数据库
        async with sessionmaker() as session:
            # library.new 事件使用专门的表
            if event_type == EVENT_TYPE_LIBRARY_NEW:
                notification = LibraryNewNotificationModel(
                    title=event_title,
                    type=event_type,
                    status=event_status,
                    item_id=item_id,
                    item_name=item_name,
                    item_type=item_type,
                    series_id=series_id,
                    series_name=series_name,
                    season_number=season_number,
                    episode_number=episode_number,
                    payload=payload
                )
            else:
                # 其他事件仍使用原来的表
                notification = NotificationModel(
                    title=event_title,
                    type=event_type,
                    status=event_status,  # library.new 事件有状态，其他事件状态为 None
                    item_id=item_id,
                    item_name=item_name,
                    item_type=item_type,
                    series_id=series_id,
                    series_name=series_name,
                    season_number=season_number,
                    episode_number=episode_number,
                    payload=payload
                )
            session.add(notification)
            await session.commit()
            await session.refresh(notification)

            # 记录入库日志
            logger.info(f"💾 通知入库, 标题: {event_title}, 事件类型: {event_type}, 状态: {event_status}")

        # 针对 library.new 事件的特殊处理
        if event_type == EVENT_TYPE_LIBRARY_NEW and not item_id:
            logger.warning("⚠️ Webhook 载荷中缺少 Item.Id")
    else:
        logger.warning("⚠️ Webhook 载荷中缺少事件类型")

    format_json_pretty(payload)
    # logger.debug("📥 Emby Webhook 详细载荷:\n{}", pretty)

    return {
        "status": "ok",
        "x_emby_event": x_emby_event,
        "processed": bool(event_type)  # 只要有事件类型就认为是已处理
    }


async def _process_playback_start(payload: dict[str, Any]) -> None:
    """处理播放开始事件，检测网页端播放并警告"""
    # 1. 检查是否为网页端
    session_info = payload.get("Session", {})
    client = session_info.get("Client", "")
    device_name = session_info.get("DeviceName", "")

    # 简单的网页端检测逻辑: Client 通常是 "Emby Web", DeviceName 可能包含 "Web"
    is_web = "Emby Web" in client or "Web" in device_name
    if not is_web:
        return

    user_info = payload.get("User", {})
    user_id = user_info.get("Id")
    if not user_id:
        return

    logger.info(f"🔍 检测到用户 {user_id} 使用网页端播放 (Client: {client}, Device: {device_name})")

    async with sessionmaker() as session:
        # 2. 检查白名单
        whitelist_val = await get_config(session, CONFIG_KEY_EMBY_WHITELIST_USER_IDS)
        whitelist: list[str] = []
        if isinstance(whitelist_val, list):
            whitelist = [str(x) for x in whitelist_val]
        elif isinstance(whitelist_val, str):
            try:
                loaded = json.loads(whitelist_val)
                if isinstance(loaded, list):
                    whitelist = [str(x) for x in loaded]
                else:
                    whitelist = [x.strip() for x in whitelist_val.split(",") if x.strip()]
            except Exception:
                whitelist = [x.strip() for x in whitelist_val.split(",") if x.strip()]

        if str(user_id) in whitelist:
            logger.info(f"✅ 用户 {user_id} 在白名单中，跳过网页端播放警告")
            return

        # 3. 获取用户数据
        result = await session.execute(select(EmbyUserModel).where(EmbyUserModel.emby_user_id == str(user_id)))
        emby_user = result.scalar_one_or_none()

        if not emby_user:
            logger.warning(f"⚠️ 用户 {user_id} 不在本地数据库中，无法记录警告")
            return

        # 4. 检查冷却时间和更新警告
        extra_data = dict(emby_user.extra_data) if emby_user.extra_data else {}
        web_warning = extra_data.get("web_playback_warning", {})

        last_warning_time_str = web_warning.get("last_warning_time")
        if last_warning_time_str:
            last_time = parse_formatted_datetime(last_warning_time_str)
            if last_time and (now() - last_time < timedelta(minutes=10)):
                logger.info(f"⏳ 用户 {user_id} 处于警告冷却期，跳过")
                return

        # 更新计数
        count = web_warning.get("count", 0) + 1
        web_warning["count"] = count
        web_warning["last_warning_time"] = format_datetime(now())

        # 记录历史
        history = web_warning.get("history", [])
        item = payload.get("Item", {})
        history.append({
            "time": format_datetime(now()),
            "item_name": item.get("Name"),
            "item_id": item.get("Id"),
            "client": client,
            "device": device_name,
        })
        web_warning["history"] = history

        extra_data["web_playback_warning"] = web_warning

        # 显式赋值以触发更新
        emby_user.extra_data = extra_data
        session.add(emby_user)
        await session.commit()

        # 5. 发送警告和执行封禁
        emby_client = get_emby_client()
        if not emby_client:
            logger.error("❌ Emby 客户端未配置，无法发送警告")
            return

        session_id = session_info.get("Id")
        if session_id:
            msg_data = _get_warning_message(count)
            try:
                await emby_client.send_session_message(
                    session_id,
                    msg_data["Header"],
                    msg_data["Text"]
                )
                logger.info(f"🔔 已向用户 {user_id} 发送第 {count} 次网页播放警告")
            except Exception as e:
                logger.error(f"❌ 发送警告消息失败: {e}")

        if count >= 3:
            logger.info(f"🚨 用户 {user_id} 达到警告上限，执行封禁")
            try:
                # 获取完整的 Policy 并修改 IsDisabled
                policy = await emby_client.get_user_policy(str(user_id))
                if policy:
                    policy["IsDisabled"] = True
                    await emby_client.update_user_policy(str(user_id), policy)
                    logger.info(f"🚫 用户 {user_id} 已成功封禁")
            except Exception as e:
                logger.error(f"❌ 封禁用户失败: {e}")


def _get_warning_message(count: int) -> dict[str, str]:
    if count == 1:
        return {
            "Header": "桜色男孩⚣｜网页播放小侦测 🤖",
            "Text": "哎呀～被我发现啦 👀\n\n你正在用【网页端播放】。\n这里暂时不支持这种打开方式哦～\n\n换成客户端继续看吧！\n这次我就当没看见 😉"
        }
    elif count == 2:
        return {
            "Header": "桜色男孩⚣｜你又来了嘛 😳",
            "Text": "嗯？怎么还是【网页端播放】呀～\n\n我已经提醒过一次啦。\n再继续这样看下去，账号可能会被关进“小黑屋”哦…\n\n快换客户端吧，别让我难做 🥺"
        }
    else:
        return {
            "Header": "桜色男孩⚣｜我真的要动手了 🚨",
            "Text": "第三次检测到【网页端播放】。\n\n规则说话，我也没办法啦。\n你的账号已被自动禁用。\n\n需要解封的话，请联系管理员～"
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
