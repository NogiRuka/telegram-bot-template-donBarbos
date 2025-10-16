from aiogram import Router, types
from aiogram.filters import CommandStart

from bot.keyboards.inline.menu import main_keyboard
from bot.services.analytics import analytics

router = Router(name="start")


@router.message(CommandStart())
@analytics.track_event("Sign Up")
async def start_handler(message: types.Message) -> None:
    """
    欢迎消息处理器
    
    参数:
        message: Telegram消息对象
    
    返回:
        None
    """
    await message.answer("欢迎使用机器人！", reply_markup=main_keyboard())
