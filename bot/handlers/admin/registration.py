from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import (
    KEY_ADMIN_OPEN_REGISTRATION_WINDOW,
    KEY_REGISTRATION_FREE_OPEN,
)
from bot.core.config import settings
from bot.database.models.config import ConfigType
from bot.keyboards.inline.buttons import (
    BACK_TO_ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
)
from bot.keyboards.inline.constants import OPEN_REGISTRATION_LABEL
from bot.services.config_service import (
    get_config,
    set_config,
)
from bot.services.main_message import MainMessageService
from bot.utils.datetime import format_datetime, get_friendly_timezone_name, now, parse_formatted_datetime
from bot.utils.permissions import require_admin_feature, require_admin_priv
from bot.utils.text import escape_markdown_v2

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

    await main_msg.update_on_callback(callback, caption, kb)
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
    current = await get_config(session, KEY_REGISTRATION_FREE_OPEN)
    new_val = not current
    await set_config(
        session,
        KEY_REGISTRATION_FREE_OPEN,
        new_val,
        ConfigType.BOOLEAN,
        default_value=False,
        operator_id=callback.from_user.id
    )
    caption, kb = await _build_reg_kb(session)
    await main_msg.update_on_callback(callback, caption, kb)
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

    # 使用工具函数获取当前时间并使用统一格式存储
    start_dt = now()
    formatted_start = start_dt.strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "start_time": formatted_start,
        "duration_minutes": duration,
        "duration_seconds": duration * 60,
    }
    await set_config(
        session,
        KEY_ADMIN_OPEN_REGISTRATION_WINDOW,
        payload,
        ConfigType.JSON,
        operator_id=callback.from_user.id
    )
    caption, kb = await _build_reg_kb(session)
    await main_msg.update_on_callback(callback, caption, kb)
    await callback.answer(f"🟢 已设置时间窗: {duration} 分钟")


@router.callback_query(F.data == "admin:open_registration:clear")
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def clear_registration_window(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """清除注册时间窗

    功能说明:
    - 清除已设置的注册时间窗配置
    - 刷新面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    await set_config(
        session,
        KEY_ADMIN_OPEN_REGISTRATION_WINDOW,
        None,
        ConfigType.JSON,
        operator_id=callback.from_user.id
    )
    caption, kb = await _build_reg_kb(session)
    await main_msg.update_on_callback(callback, caption, kb)
    await callback.answer("🟢 已清除时间窗设置")


@router.message(F.text.regexp(r"^\d{8}\.(\d{4}|\d{6})\.\d{1,4}(?:\.\d{1,2})?$"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def input_registration_window(message: Message, session: AsyncSession, main_msg: MainMessageService) -> None:
    """解析管理员输入的时间窗并应用

    功能说明:
    - 输入格式 `YYYYMMDD.HHmm[ss].MM[.SS]`，其中秒数可省略
      例如 `20251130.2300.10`、`20251130.230011.10` 或 `20251130.230011.10.11`
      上述分别表示:
      - 23:00:00 开始, 持续 10 分钟
      - 23:00:11 开始, 持续 10 分钟
      - 23:00:11 开始, 持续 10 分钟 11 秒
    - 应用后删除管理员输入消息, 保持对话整洁, 并编辑原面板消息显示状态

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        text = (message.text or "").strip()
        parts = text.split(".")
        if len(parts) == 3:
            date_part, time_part, dur_min_part = parts
            dur_sec_part = None
        elif len(parts) == 4:
            date_part, time_part, dur_min_part, dur_sec_part = parts
        else:
            raise ValueError("invalid parts length")

        year = int(date_part[0:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[0:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6]) if len(time_part) == 6 else 0

        dur_minutes = int(dur_min_part)
        dur_seconds = int(dur_sec_part) if dur_sec_part is not None else 0

        if not (0 <= dur_seconds < 60):
            raise ValueError("invalid seconds")
    except ValueError:
        await message.answer("🔴 输入格式错误, 示例: 20251130.2300.10")
        return

    # 输入时间已经是配置时区的时间，直接使用统一格式存储
    start_dt = datetime(year, month, day, hour, minute, second)
    formatted_start = start_dt.strftime("%Y-%m-%d %H:%M:%S")

    total_seconds = dur_minutes * 60 + dur_seconds
    payload = {"start_time": formatted_start, "duration_seconds": total_seconds}
    await set_config(
        session,
        KEY_ADMIN_OPEN_REGISTRATION_WINDOW,
        payload,
        ConfigType.JSON,
        operator_id=message.from_user.id
    )
    with logger.catch():
        await main_msg.delete_input(message)

    # 更新主消息内容
    uid = message.from_user.id if message.from_user else None
    if uid is None:
        return
    caption, kb = await _build_reg_kb(session)
    await main_msg.render(uid, caption, kb)


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
    free_open = await get_config(session, KEY_REGISTRATION_FREE_OPEN) or False
    window = await get_config(session, KEY_ADMIN_OPEN_REGISTRATION_WINDOW) or {}

    start_time = window.get("start_time")
    duration_minutes = window.get("duration_minutes")
    duration_seconds = window.get("duration_seconds")

    # 计算结束时间
    end_str = "未设置"
    formatted_start = "未设置"
    readable_duration = "不限"

    if start_time:
        dt = parse_formatted_datetime(start_time)
        if dt:
            formatted_start = format_datetime(dt)
            total_seconds = None
            if duration_seconds is not None:
                total_seconds = int(duration_seconds)
            elif duration_minutes is not None:
                total_seconds = int(duration_minutes) * 60

            if total_seconds is not None:
                # 计算结束时间
                end_dt = dt + timedelta(seconds=total_seconds)
                end_str = format_datetime(end_dt)
                logger.debug(f"✅ [_build_reg_kb] 计算结束时间成功: {end_str}")

                # 构造可读的持续时长
                mins, secs = divmod(total_seconds, 60)
                if mins and secs:
                    readable_duration = f"{mins} 分钟 {secs} 秒"
                elif mins:
                    readable_duration = f"{mins} 分钟"
                elif secs:
                    readable_duration = f"{secs} 秒"
                else:
                    readable_duration = "0 秒"
        else:
            formatted_start = start_time
            logger.warning(f"❌ [_build_reg_kb] 无法解析时间: {start_time}")

    # 如果没有秒级配置但有分钟配置，仍然给出可读时长
    if readable_duration == "不限" and duration_minutes is not None and duration_seconds is None:
        try:
            m = int(duration_minutes)
            readable_duration = f"{m} 分钟" if m > 0 else "不限"
        except Exception:
            pass

    # 转义 MarkdownV2 特殊字符
    formatted_start = escape_markdown_v2(formatted_start)
    end_str = escape_markdown_v2(end_str)
    readable_duration = escape_markdown_v2(readable_duration)
    tz_name = escape_markdown_v2(get_friendly_timezone_name(settings.TIMEZONE))

    status_line = f"注册状态：{'🟢 开启' if free_open else '🔴 关闭'}\n"
    example_base = now().strftime("%Y%m%d.%H%M")
    caption = (
        f"*{OPEN_REGISTRATION_LABEL}*\n\n"
        + status_line
        + f"开始时间：{formatted_start}\n"
        + f"结束时间：{end_str}\n"
        + f"持续时长：{readable_duration}\n\n"
        + f"输入格式示例：`{example_base}.10` 或 `YYYYMMDD.HHmmss.MM.SS`\n"
        + f"时区：{tz_name}"
    )
    logger.debug("✅ [_build_reg_kb] 生成 caption 成功")

    rows: list[list[InlineKeyboardButton]] = []
    rows.append([
        InlineKeyboardButton(
            text=("🔴 关闭自由注册" if free_open else "🟢 开启自由注册"),
            callback_data="admin:open_registration:toggle_free",
        )
    ])
    rows.append([
        InlineKeyboardButton(text="5分钟", callback_data="admin:open_registration:set:5"),
        InlineKeyboardButton(text="10分钟", callback_data="admin:open_registration:set:10"),
        InlineKeyboardButton(text="30分钟", callback_data="admin:open_registration:set:30"),
        InlineKeyboardButton(text="60分钟", callback_data="admin:open_registration:set:60"),
    ])

    if start_time or duration_minutes is not None or duration_seconds is not None:
        rows.append([
            InlineKeyboardButton(text="❌ 清除时间窗设置", callback_data="admin:open_registration:clear")
        ])

    rows.append([BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    logger.debug("✅ [_build_reg_kb] 键盘构建完成")
    return caption, kb
