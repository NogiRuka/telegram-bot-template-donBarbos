from pathlib import Path

from aiogram import Router, types
from aiogram.filters import CommandStart

from bot.keyboards.inline.start_user import get_start_user_keyboard
from bot.keyboards.inline.start_admin import get_start_admin_keyboard
from bot.keyboards.inline.start_owner import get_start_owner_keyboard
from bot.services.analytics import analytics
from bot.handlers.menu import render_view

router = Router(name="start")


@router.message(CommandStart())
@analytics.track_event("Sign Up")
async def start_handler(message: types.Message, role: str) -> None:
    """欢迎消息处理器

    功能说明:
    - 根据角色显示不同首页界面与按钮

    输入参数:
    - message: Telegram消息对象
    - role: 用户角色标识

    返回值:
    - None
    """
    image = "assets/sakura.png"
    if role == "owner":
        kb = get_start_owner_keyboard()
        caption = "🌸 所有者欢迎页"
    elif role == "admin":
        kb = get_start_admin_keyboard()
        caption = "🌸 管理员欢迎页"
    else:
        kb = get_start_user_keyboard()
        caption = "🌸 欢迎使用机器人！"
    await render_view(message, image, caption, kb)
