from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.admin import get_quiz_admin_keyboard
from bot.services.quiz_config_service import QuizConfigService
from bot.utils.permissions import require_admin_feature
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from .router import router

@router.callback_query(F.data.in_({QUIZ_ADMIN_CALLBACK_DATA, "quiz_admin:menu"}))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_quiz_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """显示问答管理菜单"""
    await state.clear()
    
    # 获取当前配置状态
    prob = await QuizConfigService.get_trigger_probability(session)
    cooldown = await QuizConfigService.get_cooldown_minutes(session)
    daily = await QuizConfigService.get_daily_limit(session)
    
    text = (
        "<b>🎲 问答管理</b>\n\n"
        f"当前配置：\n"
        f"• 触发概率: {prob:.0%}\n"
        f"• 冷却时间: {cooldown}分钟\n"
        f"• 每日上限: {daily}次\n\n"
        "请选择操作："
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_quiz_admin_keyboard()
    )
