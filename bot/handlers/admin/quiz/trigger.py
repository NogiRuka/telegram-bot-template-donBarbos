from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import (
    KEY_ADMIN_QUIZ,
    KEY_QUIZ_COOLDOWN_MINUTES,
    KEY_QUIZ_DAILY_LIMIT,
    KEY_QUIZ_SESSION_TIMEOUT,
    KEY_QUIZ_TRIGGER_PROBABILITY,
)
from bot.database.models.config import ConfigType
from bot.keyboards.inline.admin import get_quiz_trigger_keyboard
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService
from bot.states.admin import QuizAdminState
from bot.utils.permissions import require_admin_feature


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":trigger")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_trigger_settings(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示触发设置"""
    prob = await get_config(session, KEY_QUIZ_TRIGGER_PROBABILITY)
    cooldown = await get_config(session, KEY_QUIZ_COOLDOWN_MINUTES)
    daily = await get_config(session, KEY_QUIZ_DAILY_LIMIT)
    timeout = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)

    text = (
        f"*⚙️ 触发设置*\n\n"
        f"🎲 触发概率：{prob:.1%} \\(每次交互\\)\n"
        f"⏳ 冷却时间：{cooldown} 分钟\n"
        f"🔢 每日上限：{daily} 次\n"
        f"⏱️ 答题限时：{timeout} 秒"
    ).replace(".", "\\.")
    await main_msg.update_on_callback(callback, text, get_quiz_trigger_keyboard())

@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":set"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def ask_setting_value(callback: CallbackQuery, state: FSMContext) -> None:
    """请求输入设置值"""
    setting_type = callback.data.split(":")[-1]
    await state.update_data(setting_type=setting_type)

    prompts = {
        "probability": "请输入新的触发概率 (0.0 - 1.0)，例如 0.05 表示 5%",
        "cooldown": "请输入新的冷却时间 (分钟，整数)",
        "daily_limit": "请输入新的每日触发上限 (整数)",
        "timeout": "请输入新的答题限时 (秒，整数)"
    }

    await callback.message.answer(prompts.get(setting_type, "请输入新值"))
    await state.set_state(QuizAdminState.waiting_for_setting_value)
    await callback.answer()

@router.message(QuizAdminState.waiting_for_setting_value)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def process_setting_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """处理设置值输入"""
    data = await state.get_data()
    setting_type = data.get("setting_type")
    value_str = message.text

    try:
        if setting_type == "probability":
            val = float(value_str)
            if not (0 <= val <= 1): raise ValueError
            await set_config(session, KEY_QUIZ_TRIGGER_PROBABILITY, val, ConfigType.FLOAT, operator_id=message.from_user.id)

        elif setting_type == "cooldown":
            val = int(value_str)
            await set_config(session, KEY_QUIZ_COOLDOWN_MINUTES, val, ConfigType.INTEGER, operator_id=message.from_user.id)

        elif setting_type == "daily_limit":
            val = int(value_str)
            await set_config(session, KEY_QUIZ_DAILY_LIMIT, val, ConfigType.INTEGER, operator_id=message.from_user.id)

        elif setting_type == "timeout":
            val = int(value_str)
            await set_config(session, KEY_QUIZ_SESSION_TIMEOUT, val, ConfigType.INTEGER, operator_id=message.from_user.id)

        await message.answer("✅ 设置已更新！")
        await state.clear()

    except ValueError:
        await message.answer("⚠️ 输入无效，请重试。")
