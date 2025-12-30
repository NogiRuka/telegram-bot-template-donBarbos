from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.quiz_admin import quiz_admin_menu_kb
from bot.utils.permissions import require_admin_feature
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from .router import router

@router.callback_query(F.data.in_({QUIZ_ADMIN_CALLBACK_DATA, "quiz_admin:menu"}))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_quiz_menu(callback: CallbackQuery, state: FSMContext):
    """显示问答管理菜单"""
    await state.clear()
    await callback.message.edit_text(
        "🎲 <b>问答管理</b>\n\n请选择操作：",
        reply_markup=quiz_admin_menu_kb()
    )
