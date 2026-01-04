import contextlib

from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_NOTIFICATION_CHANNELS
from bot.database.models.config import ConfigType
from bot.keyboards.inline.admin import get_notification_settings_keyboard
from bot.keyboards.inline.constants import (
    NOTIFY_SETTINGS_CALLBACK_DATA,
    NOTIFY_SETTINGS_LABEL,
    NOTIFY_SETTINGS_TOGGLE_CALLBACK_DATA,
)
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService


@router.callback_query(F.data == NOTIFY_SETTINGS_CALLBACK_DATA)
async def notification_settings_handler(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理通知设置菜单请求"""
    # 获取配置
    channels_config = await get_config(session, KEY_NOTIFICATION_CHANNELS)
    if not channels_config:
        channels_config = []
    elif not isinstance(channels_config, list):
        # 防御性编程
        channels_config = []

    # 渲染键盘
    keyboard = get_notification_settings_keyboard(channels_config)

    # 更新界面
    # 使用 Markdown 格式美化
    text = (
        f"*{NOTIFY_SETTINGS_LABEL}*\n\n"
        "📢 请点击下方按钮切换频道的启用/禁用状态："
    )

    await main_msg.update_on_callback(callback, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith(NOTIFY_SETTINGS_TOGGLE_CALLBACK_DATA))
async def notification_settings_toggle_handler(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理频道开关切换请求"""
    # 解析 ID
    # callback data: "admin:notify_settings:toggle:{channel_id}"
    try:
        prefix = f"{NOTIFY_SETTINGS_TOGGLE_CALLBACK_DATA}:"
        if not callback.data.startswith(prefix):
             await callback.answer("⚠️ 无效的请求数据", show_alert=True)
             return

        channel_id = callback.data[len(prefix):]
    except ValueError:
        await callback.answer("⚠️ 无效的请求", show_alert=True)
        return

    # 获取现有配置
    channels_config = await get_config(session, KEY_NOTIFICATION_CHANNELS)
    if not channels_config or not isinstance(channels_config, list):
        channels_config = []

    # 查找并更新
    found = False
    new_status = False
    channel_name = "未知频道"

    for ch in channels_config:
        if isinstance(ch, dict) and str(ch.get("id")) == channel_id:
            current = ch.get("enabled", True)
            new_status = not current
            ch["enabled"] = new_status
            channel_name = ch.get("name", channel_id)
            found = True
            break

    if found:
        # 保存更新
        await set_config(
            session,
            KEY_NOTIFICATION_CHANNELS,
            channels_config,
            config_type=ConfigType.JSON,
            operator_id=callback.from_user.id
        )

        # 重新渲染
        keyboard = get_notification_settings_keyboard(channels_config)

        text = (
            f"*{NOTIFY_SETTINGS_LABEL}*\n\n"
            "📢 请点击下方按钮切换频道的启用/禁用状态："
        )

        # 更新消息
        with contextlib.suppress(Exception):
            await main_msg.update_on_callback(callback, text, keyboard)

        status_text = "启用" if new_status else "禁用"
        await callback.answer(f"✅ 已{status_text}频道: {channel_name}")
    else:
        await callback.answer("❌ 找不到该频道配置", show_alert=True)
