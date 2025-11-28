from aiogram import Router, types
from aiogram.filters import Command

from bot.keyboards.inline.menu import main_keyboard

router = Router(name="menu")


@router.message(Command(commands=["menu", "main"]))
async def menu_handler(message: types.Message) -> None:
    """主菜单处理器

    功能说明:
    - 调用一言接口获取句子作为主面板文案并展示内联菜单

    输入参数:
    - message: Telegram消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await message.answer("主菜单", reply_markup=main_keyboard())
