from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="info")


@router.message(Command(commands=["info", "help", "about"]))
async def info_handler(message: types.Message) -> None:
    """
    机器人信息处理器
    
    参数:
        message: Telegram消息对象
    
    返回:
        None
    """
    await message.answer("这是一个Telegram机器人，提供各种功能服务。")
