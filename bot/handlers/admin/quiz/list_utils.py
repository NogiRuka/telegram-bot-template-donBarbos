from aiogram import Bot
from aiogram.fsm.context import FSMContext
from bot.utils.message import safe_delete_message


async def _clear_quiz_list(state: FSMContext, bot: Bot, chat_id: int) -> None:
    """清理已发送的列表消息"""
    data = await state.get_data()
    msg_ids = data.get("quiz_list_ids", [])
    if not msg_ids:
        return

    for msg_id in msg_ids:
        await safe_delete_message(bot, chat_id, msg_id)

    await state.update_data(quiz_list_ids=[])
