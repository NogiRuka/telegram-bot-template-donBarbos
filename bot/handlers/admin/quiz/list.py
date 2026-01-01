from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.admin import get_quiz_list_keyboard
from bot.keyboards.inline.constants import QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.message import clear_message_list_from_state
from bot.utils.permissions import require_admin_feature


@router.callback_query(F.data == QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_list_menu(callback: CallbackQuery, main_msg: MainMessageService, state: FSMContext) -> None:
    """显示查看列表菜单"""
    await clear_message_list_from_state(state, callback.bot, callback.message.chat.id, "quiz_list_ids")

    text = (
        "*📋 查看列表*\n\n"
        "请选择要查看的内容："
    )
    await main_msg.update_on_callback(callback, text, get_quiz_list_keyboard())
    await callback.answer()
