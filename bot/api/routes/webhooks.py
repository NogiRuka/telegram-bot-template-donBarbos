"""
Webhooks 路由
处理来自 Emby 的 Webhook 回调请求
"""

from __future__ import annotations
import json
from datetime import timedelta
from typing import TYPE_CHECKING, Annotated, Any

from aiogram.exceptions import TelegramAPIError
from aiohttp import ClientError
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from bot.config.constants import KEY_EMBY_WHITELIST_USER_IDS, KEY_TG_WHITELIST_USER_IDS
from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    EVENT_TYPE_PLAYBACK_START,
)
from bot.core.loader import bot as telegram_bot
from bot.database.database import sessionmaker
from bot.database.models.emby_user import EmbyUserModel
from bot.database.models.library_new_notification import LibraryNewNotificationModel
from bot.database.models.notification import NotificationModel
from bot.database.models.user_extend import UserExtendModel
from bot.services.config_service import get_config
from bot.services.emby_update_helper import detect_and_update_emby_user
from bot.utils.datetime import format_datetime, now, parse_formatted_datetime
from bot.utils.emby import get_emby_client

try:
    import orjson
except ImportError:
    orjson = None
from loguru import logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

WARNING_COOLDOWN_MINUTES = 10
WARNING_SECOND = 2
WARNING_DISABLE_THRESHOLD = 3


def _parse_whitelist(whitelist_val: Any) -> list[str]:
    if isinstance(whitelist_val, list):
        return [str(x) for x in whitelist_val]
    if isinstance(whitelist_val, str):
        loaded: Any | None
        try:
            loaded = json.loads(whitelist_val)
        except json.JSONDecodeError:
            loaded = None
        if isinstance(loaded, list):
            return [str(x) for x in loaded]
        return [x.strip() for x in whitelist_val.split(",") if x.strip()]
    return []


async def _get_emby_user_and_extend(
    session: AsyncSession,
    user_id: str,
) -> tuple[EmbyUserModel, UserExtendModel | None] | None:
    stmt = select(EmbyUserModel, UserExtendModel).outerjoin(
        UserExtendModel,
        UserExtendModel.emby_user_id == EmbyUserModel.emby_user_id,
    ).where(EmbyUserModel.emby_user_id == user_id)
    result = await session.execute(stmt)
    record = result.first()
    if not record:
        return None
    emby_user, user_extend = record
    return emby_user, user_extend


async def _increment_warning(
    session: AsyncSession,
    emby_user: EmbyUserModel,
    warning_key: str,
    client_device: tuple[str, str],
    item: dict[str, Any],
) -> int | None:
    client, device_name = client_device
    extra_data = dict(emby_user.extra_data) if emby_user.extra_data else {}
    warning_data = extra_data.get(warning_key, {})

    last_warning_time_str = warning_data.get("last_warning_time")
    if last_warning_time_str:
        last_time = parse_formatted_datetime(last_warning_time_str)
        if last_time and (now() - last_time < timedelta(minutes=WARNING_COOLDOWN_MINUTES)):
            return None

    count = int(warning_data.get("count", 0)) + 1
    warning_data["count"] = count
    warning_data["last_warning_time"] = format_datetime(now())

    history = warning_data.get("history", [])
    history.append(
        {
            "time": format_datetime(now()),
            "item_name": item.get("Name"),
            "item_id": item.get("Id"),
            "client": client,
            "device": device_name,
        }
    )
    warning_data["history"] = history

    extra_data[warning_key] = warning_data
    emby_user.extra_data = extra_data
    flag_modified(emby_user, "extra_data")
    session.add(emby_user)
    await session.commit()
    return count


async def _send_telegram_warning(
    *,
    user_extend: UserExtendModel | None,
    emby_user_id: str,
    text: str,
    count: int,
    label: str,
) -> None:
    if user_extend and user_extend.user_id:
        try:
            await telegram_bot.send_message(chat_id=user_extend.user_id, text=text)
            logger.info(f"🔔 已向用户 {user_extend.user_id} 发送{label} (第 {count} 次)")
        except (TelegramAPIError, ClientError, RuntimeError, ValueError) as e:
            logger.error(f"❌ 发送 Telegram 警告失败: {e}")
        return
    logger.warning(f"⚠️ 用户 {emby_user_id} 未绑定 Telegram 账号，无法发送警告")


async def _send_emby_session_warning(
    emby_client: Any,
    session_id: str,
    header: str,
    text: str,
) -> bool:
    try:
        await emby_client.send_session_message(session_id, header, text)
    except (ClientError, RuntimeError, ValueError) as e:
        logger.error(f"❌ 发送警告消息失败: {e}")
    else:
        return True
    return False


def _is_web_playback(client: str, device_name: str) -> bool:
    return "Emby Web" in client or "Web" in device_name


def _is_restricted_client(client: str, device_name: str) -> bool:
    keywords = ["网易", "爆米花"]
    return any(k in client for k in keywords) or any(k in device_name for k in keywords)


async def _is_user_in_whitelist(session: AsyncSession, user_id: str) -> bool:
    # Emby 用户ID白名单
    emby_whitelist_val = await get_config(session, KEY_EMBY_WHITELIST_USER_IDS)
    emby_whitelist = set(_parse_whitelist(emby_whitelist_val))
    if user_id in emby_whitelist:
        return True
    # Telegram 用户ID白名单（需要关联 UserExtend）
    tg_whitelist_val = await get_config(session, KEY_TG_WHITELIST_USER_IDS)
    tg_whitelist: set[int] = set()
    for x in _parse_whitelist(tg_whitelist_val):
        sid = str(x).strip()
        if not sid.isdigit():
            continue
        uid = int(sid)
        if uid <= 0:
            continue
        tg_whitelist.add(uid)
    if not tg_whitelist:
        return False
    # 查询 emby_user_id 对应的 telegram user_id
    stmt = select(UserExtendModel.user_id).where(UserExtendModel.emby_user_id == user_id)
    res = await session.execute(stmt)
    tg_id = res.scalar_one_or_none()
    return tg_id in tg_whitelist if tg_id is not None else False


async def _maybe_disable_user_for_web_playback(
    session: AsyncSession,
    emby_client: Any,
    emby_user: EmbyUserModel,
    user_id: str,
) -> None:
    success = await emby_client.disable_user(user_id)
    if not success:
        return

    new_user_dto = await emby_client.get_user(user_id)
    detect_and_update_emby_user(
        model=emby_user,
        new_user_dto=new_user_dto or emby_user.user_dto or {},
        session=session,
        force_update=True,
        extra_remark="系统自动封禁：网页端播放违规 (3次警告)",
    )

    if not emby_user.extra_data:
        emby_user.extra_data = {}
    emby_user.extra_data["is_disabled"] = True
    emby_user.extra_data["disabled_reason"] = "web_playback_violation"
    emby_user.extra_data["disabled_at"] = format_datetime(now())

    flag_modified(emby_user, "extra_data")
    session.add(emby_user)
    await session.commit()
    logger.info(f"💾 已更新用户 {user_id} 数据库状态为封禁，并保存历史快照")
    logger.info(f"🚫 用户 {user_id} 已成功封禁")


async def _handle_web_playback_warning(
    session: AsyncSession,
    payload: dict[str, Any],
    user_id: str,
    session_info: dict[str, Any],
) -> None:
    session_id = session_info.get("Id")
    client = session_info.get("Client", "")
    device_name = session_info.get("DeviceName", "")

    record = await _get_emby_user_and_extend(session, user_id)
    if not record:
        logger.warning(f"⚠️ 用户 {user_id} 不在本地数据库中，无法记录警告")
        return
    emby_user, user_extend = record

    item = payload.get("Item", {})
    count = await _increment_warning(
        session=session,
        emby_user=emby_user,
        warning_key="web_playback_warning",
        client_device=(client, device_name),
        item=item,
    )
    if count is None:
        logger.info(f"⏳ 用户 {user_id} 处于警告冷却期，跳过")
        return

    msg_data = _get_warning_message(count)
    msg_text = f"{msg_data['Header']}\n\n{msg_data['Text']}"
    await _send_telegram_warning(
        user_extend=user_extend,
        emby_user_id=user_id,
        text=msg_text,
        count=count,
        label="网页端播放警告",
    )

    emby_client = get_emby_client()
    if not emby_client:
        logger.error("❌ Emby 客户端未配置，无法发送警告")
        return

    if session_id:
        ok = await _send_emby_session_warning(
            emby_client,
            str(session_id),
            msg_data["Header"],
            msg_data["Text"],
        )
        if ok:
            logger.info(f"🔔 已向用户 {user_id} 发送第 {count} 次网页端播放警告")

    if count >= WARNING_DISABLE_THRESHOLD:
        logger.info(f"🚨 用户 {user_id} 达到警告上限，执行封禁")
        try:
            await _maybe_disable_user_for_web_playback(session, emby_client, emby_user, user_id)
        except (ClientError, RuntimeError, ValueError) as e:
            logger.error(f"❌ 封禁用户失败: {e}")


async def _maybe_disable_user_for_restricted_client(
    session: AsyncSession,
    emby_client: Any,
    emby_user: EmbyUserModel,
    user_id: str,
) -> None:
    success = await emby_client.disable_user(user_id)
    if not success:
        return

    new_user_dto = await emby_client.get_user(user_id)
    detect_and_update_emby_user(
        model=emby_user,
        new_user_dto=new_user_dto or emby_user.user_dto or {},
        session=session,
        force_update=True,
        extra_remark="系统自动封禁：使用违规客户端 (3次警告)",
    )

    if not emby_user.extra_data:
        emby_user.extra_data = {}
    emby_user.extra_data["is_disabled"] = True
    emby_user.extra_data["disabled_reason"] = "restricted_client_violation"
    emby_user.extra_data["disabled_at"] = format_datetime(now())

    flag_modified(emby_user, "extra_data")
    session.add(emby_user)
    await session.commit()
    logger.info(f"💾 已更新用户 {user_id} 数据库状态为封禁，并保存历史快照")
    logger.info(f"🚫 用户 {user_id} 已成功封禁")


async def _handle_restricted_client_warning(
    session: AsyncSession,
    payload: dict[str, Any],
    user_id: str,
    client: str,
    device_name: str,
) -> None:
    record = await _get_emby_user_and_extend(session, user_id)
    if not record:
        logger.warning(f"⚠️ 用户 {user_id} 不在本地数据库中，无法记录警告")
        return
    emby_user, user_extend = record

    item = payload.get("Item", {})
    count = await _increment_warning(
        session=session,
        emby_user=emby_user,
        warning_key="restricted_client_warning",
        client_device=(client, device_name),
        item=item,
    )
    if count is None:
        logger.info(f"⏳ 用户 {user_id} 处于违规客户端警告冷却期，跳过")
        return

    msg_text = _get_restricted_client_warning_text(count)
    await _send_telegram_warning(
        user_extend=user_extend,
        emby_user_id=user_id,
        text=msg_text,
        count=count,
        label="违规客户端警告",
    )

    if count < WARNING_DISABLE_THRESHOLD:
        return

    logger.info(f"🚨 用户 {user_id} 达到违规客户端警告上限，执行封禁")
    emby_client = get_emby_client()
    if not emby_client:
        logger.error("❌ Emby 客户端未配置，无法执行封禁")
        return

    try:
        await _maybe_disable_user_for_restricted_client(session, emby_client, emby_user, user_id)
    except (ClientError, RuntimeError, ValueError) as e:
        logger.error(f"❌ 封禁用户失败: {e}")


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

    # 处理非官方客户端警告（网易/爆米花）
    if payload.get("Session"):
        await _process_restricted_client_check(payload)

    # 所有事件都存入数据库，但只有 library.new 事件设置状态
    if event_type:
        # logger.info(f"📥 收到 Emby Webhook 事件: {event_type}")

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
    session_info = payload.get("Session", {})
    client = session_info.get("Client", "")
    device_name = session_info.get("DeviceName", "")

    if not _is_web_playback(client, device_name):
        return

    user_info = payload.get("User", {})
    user_id = user_info.get("Id")
    if not user_id:
        return

    logger.info(f"🔍 检测到用户 {user_id} 使用网页端播放 (Client: {client}, Device: {device_name})")

    async with sessionmaker() as session:
        if await _is_user_in_whitelist(session, str(user_id)):
            logger.info(f"✅ 用户 {user_id} 在白名单中，跳过网页端播放警告")
            return

        await _handle_web_playback_warning(
            session=session,
            payload=payload,
            user_id=str(user_id),
            session_info=session_info,
        )


def _get_warning_message(count: int) -> dict[str, str]:
    if count == 1:
        return {
            "Header": "桜色男孩⚣｜网页播放小侦测 🤖",
            "Text": (
                "哎呀～被我发现啦 👀\n\n"
                "你正在用【网页端播放】。\n"
                "这里暂时不支持这种打开方式哦～\n\n"
                "换成客户端继续看吧！\n"
                "这次我就当没看见 😉"
            ),
        }
    if count == WARNING_SECOND:
        return {
            "Header": "桜色男孩⚣｜你又来了嘛 😳",
            "Text": (
                "嗯？怎么还是【网页端播放】呀～\n\n"
                "我已经提醒过一次啦。\n"
                "再继续这样看下去，账号可能会被关进“小黑屋”哦…\n\n"
                "快换客户端吧，别让我难做 🥺"
            ),
        }
    return {
        "Header": "桜色男孩⚣｜我真的要动手了 🚨",
        "Text": (
            "第三次检测到【网页端播放】。\n\n"
            "规则说话，我也没办法啦。\n"
            "你的账号已被自动禁用。\n\n"
            "需要解封的话，请联系管理员～"
        ),
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
    if orjson is not None:
        try:
            return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")
        except TypeError:
            pass
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return json.dumps({"unserializable": str(type(data))}, ensure_ascii=False)


async def _process_restricted_client_check(payload: dict[str, Any]) -> None:
    """处理非官方客户端检测（网易/爆米花）"""
    session_info = payload.get("Session", {})
    client = session_info.get("Client", "")
    device_name = session_info.get("DeviceName", "")

    if not _is_restricted_client(client, device_name):
        return

    user_info = payload.get("User", {})
    user_id = user_info.get("Id")
    if not user_id:
        return

    logger.info(f"🔍 检测到用户 {user_id} 使用违规客户端 (Client: {client}, Device: {device_name})")

    async with sessionmaker() as session:
        if await _is_user_in_whitelist(session, str(user_id)):
            logger.info(f"✅ 用户 {user_id} 在白名单中，跳过违规客户端警告")
            return
        await _handle_restricted_client_warning(
            session=session,
            payload=payload,
            user_id=str(user_id),
            client=client,
            device_name=device_name,
        )


def _get_restricted_client_warning_text(count: int) -> str:
    if count == 1:
        return (
            "桜色男孩⚣｜客户端小侦测 🤖\n\n"
            "我发现你正在使用【网易爆米花客户端】播放内容 👀\n\n"
            "这个客户端在本服务器是被禁止使用的哦～\n"
            "请尽快更换为官方客户端观看。\n\n"
            "这次只是提醒，不会影响账号使用 😉"
        )
    if count == WARNING_SECOND:
        return (
            "桜色男孩⚣｜你又用爆米花啦 😳\n\n"
            "再次检测到你使用【网易爆米花客户端】。\n\n"
            "这个客户端不被允许使用。\n"
            "如果继续使用，账号可能会被限制访问。\n\n"
            "别让我难做呀，换个客户端吧～"
        )
    return (
        "桜色男孩⚣｜播放权限已锁定 🚨\n\n"
        "第三次检测到你使用【网易爆米花客户端】。\n\n"
        "根据服务器规则，你的账号已被自动禁用。\n"
        "如需恢复权限，请联系管理员处理。"
    )
