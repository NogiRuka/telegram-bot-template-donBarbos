from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.keyboards.inline.constants import OPEN_REGISTRATION_LABEL
from bot.services.config_service import (
    get_free_registration_status,
    get_registration_window,
    set_free_registration_status,
    set_registration_window,
)
from bot.keyboards.inline.buttons import (
    BACK_TO_ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
)
from bot.services.main_message import MainMessageService
from bot.utils.datetime import format_datetime, now, to_iso_string
from bot.utils.images import get_common_image
from bot.utils.permissions import require_admin_feature, require_admin_priv

router = Router(name="admin_registration")


@router.callback_query(F.data == "admin:open_registration")
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def open_registration_feature(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """打开开放注册面板

    功能说明:
    - 管理员点击开放注册后展示面板, 显示 `registration.free_open` 状态与时间窗
    - 底部提供自由注册开关按钮、预设时间窗按钮(1/5/30/60分钟)、返回与返回主面板按钮

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """

    caption, kb = await _build_reg_kb(session)
    logger.info(f"ℹ️ [open_registration_feature] caption内容: {caption}")

    await main_msg.update_on_callback(callback, caption, kb, get_common_image())
    await callback.answer()


@router.callback_query(F.data == "admin:open_registration:toggle_free")
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def toggle_free_registration(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """切换自由注册开关

    功能说明:
    - 翻转 `registration.free_open` 状态并刷新面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    current = await get_free_registration_status(session)
    new_val = not current
    await set_free_registration_status(session, new_val, operator_id=callback.from_user.id)
    caption, kb = await _build_reg_kb(session)
    await main_msg.update_on_callback(callback, caption, kb, get_common_image())
    await callback.answer(f"{'🟢' if new_val else '🔴'} 自由注册已{'开启' if new_val else '关闭'}")


@router.callback_query(lambda c: c.data and c.data.startswith("admin:open_registration:set:"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def set_registration_preset(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """设置预设注册时间窗

    功能说明:
    - 支持 1/5/30/60 分钟的快捷设置; 开始时间默认为北京时间当前时间

    输入参数:
    - callback: 回调对象, data 形如 `admin:open_registration:set:<minutes>`
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        minutes_str = (callback.data or "").split(":")[-1]
        duration = int(minutes_str)
    except ValueError:
        await callback.answer("🔴 参数无效", show_alert=True)
        return
    
    # 使用工具函数获取当前时间并转换为 ISO 格式
    start_dt = now()
    start_iso = to_iso_string(start_dt)
    await set_registration_window(session, start_iso, duration, operator_id=callback.from_user.id)
    caption, kb = await _build_reg_kb(session)
    await main_msg.update_on_callback(callback, caption, kb, get_common_image())
    await callback.answer(f"🟢 已设置时间窗: {duration} 分钟")


@router.message(F.text.regexp(r"^\d{8}\.\d{4}\.\d{1,4}$"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def input_registration_window(message: Message, session: AsyncSession, main_msg: MainMessageService) -> None:
    """解析管理员输入的时间窗并应用

    功能说明:
    - 输入格式 `YYYYMMDD.HHmm.DUR` (例如 20251130.2300.10), 默认为北京时间
    - 应用后删除管理员输入消息, 保持对话整洁, 并编辑原面板消息显示状态

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        text = (message.text or "").strip()
        date_part, time_part, dur_part = text.split(".")
        year = int(date_part[0:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[0:2])
        minute = int(time_part[2:4])
        duration = int(dur_part)
    except ValueError:
        await message.answer("🔴 输入格式错误, 示例: 20251130.2300.10")
        return

    beijing = timezone(timedelta(hours=8))
    start_dt = datetime(year, month, day, hour, minute, tzinfo=beijing)
    start_iso = start_dt.isoformat()
    await set_registration_window(session, start_iso, duration, operator_id=message.from_user.id)
    with logger.catch():
        await main_msg.delete_input(message)

    # 更新主消息内容
    uid = message.from_user.id if message.from_user else None
    if uid is None:
        return
    caption, kb = await _build_reg_kb(session)
    await main_msg.update(uid, caption, kb)


async def _build_reg_kb(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup]:
    """构建开放注册面板的说明与键盘

    功能说明:
    - 读取 `registration.free_open` 与 `admin.open_registration.window` 并格式化展示
    - 键盘包含自由开关、预设时间窗(1/5/30/60)、返回与返回主面板

    输入参数:
    - session: 异步数据库会话

    返回值:
    - tuple[str, InlineKeyboardMarkup]: (caption文本, 内联键盘)
    """
    logger.debug("🔍 [_build_reg_kb] 开始读取配置...")
    free_open = await get_free_registration_status(session)
    logger.debug(f"🔍 [_build_reg_kb] free_open={free_open}")

    window = await get_registration_window(session) or {}
    logger.debug(f"🔍 [_build_reg_kb] window={window}")

    start_iso = window.get("start_iso")
    duration = window.get("duration_minutes")

    # 计算结束时间
    end_str = "未设置"
    formatted_start = "未设置"
    if start_iso:
        dt = parse_iso_datetime(start_iso)
        if dt:
            formatted_start = format_datetime(dt)
            if duration is not None:
                end_dt = dt + timedelta(minutes=int(duration))
                end_str = format_datetime(end_dt)
                logger.debug(f"✅ [_build_reg_kb] 计算结束时间成功: {end_str}")
        else:
            formatted_start = start_iso
            logger.warning(f"❌ [_build_reg_kb] 无法解析时间: {start_iso}")
    status_line = f"注册状态：{'🟢 开启' if free_open else '🔴 关闭'}\n"
    caption = (
        f"{OPEN_REGISTRATION_LABEL}\n\n"
        + status_line
        + f"开始时间：{formatted_start}\n"
        + f"结束时间：{end_str}\n"
        + f"持续分钟：{duration if duration is not None else '不限'}\n\n"
        + f"输入格式示例：<code>{datetime.now().strftime('%Y%m%d.%H%M')}.10</code>\n"
        + f"时区：{settings.TIMEZONE}"
    )
    logger.debug("✅ [_build_reg_kb] 生成 caption 成功")

    rows: list[list[InlineKeyboardButton]] = []
    rows.append([
        InlineKeyboardButton(
            text=("🟢 关闭自由注册" if free_open else "🟢 开启自由注册"),
            callback_data="admin:open_registration:toggle_free",
        )
    ])
    rows.append([
        InlineKeyboardButton(text="1分钟", callback_data="admin:open_registration:set:1"),
        InlineKeyboardButton(text="10分钟", callback_data="admin:open_registration:set:10"),
        InlineKeyboardButton(text="30分钟", callback_data="admin:open_registration:set:30"),
        InlineKeyboardButton(text="60分钟", callback_data="admin:open_registration:set:60"),
    ])
    rows.append([
        [BACK_TO_ADMIN_PANEL_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    logger.debug("✅ [_build_reg_kb] 键盘构建完成")
    return caption, kb
