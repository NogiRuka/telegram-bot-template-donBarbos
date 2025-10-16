from aiogram import Router, types
from aiogram.filters import Command

from bot.keyboards.inline.contacts import contacts_keyboard

router = Router(name="support")


@router.message(Command(commands=["supports", "support", "contacts", "contact"]))
async def support_handler(message: types.Message) -> None:
    """
    支持联系处理器
    
    参数:
        message: Telegram消息对象
    
    返回:
        None
    """
    await message.answer("如需帮助，请联系我们的支持团队。", reply_markup=contacts_keyboard())
