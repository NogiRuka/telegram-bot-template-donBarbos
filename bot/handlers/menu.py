from aiogram import Router, types
from aiogram.filters import Command

from bot.keyboards.inline.menu import main_keyboard

router = Router(name="menu")


@router.message(Command(commands=["menu", "main"]))
async def menu_handler(message: types.Message) -> None:
    """
    主菜单处理器

    参数:
        message: Telegram消息对象

    返回:
        None
    """
    await message.answer("主菜单", reply_markup=main_keyboard())
