from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import (
    KEY_ADMIN_QUIZ,
    KEY_QUIZ_COOLDOWN_MINUTES,
    KEY_QUIZ_DAILY_LIMIT,
    KEY_QUIZ_TRIGGER_PROBABILITY,
)
from bot.keyboards.inline.admin import get_quiz_admin_keyboard
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.config_service import get_config
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_quiz_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """显示问答管理菜单"""
    await state.clear()

    # 获取当前配置状态
    prob = await get_config(session, KEY_QUIZ_TRIGGER_PROBABILITY)
    cooldown = await get_config(session, KEY_QUIZ_COOLDOWN_MINUTES)
    daily = await get_config(session, KEY_QUIZ_DAILY_LIMIT)

    text = (
        "*🎲 问答管理*\n\n"
        f"当前配置：\n"
        f"• 触发概率：{prob:.0%}\n"
        f"• 冷却时间：{cooldown}分钟\n"
        f"• 每日上限：{daily}次\n\n"
        "请选择操作："
    )

    await main_msg.update_on_callback(callback, text, get_quiz_admin_keyboard())
    await callback.answer()
