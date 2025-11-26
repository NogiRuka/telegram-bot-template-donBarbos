import contextlib
from pathlib import Path

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InputMediaPhoto

from bot.keyboards.inline.menu import main_keyboard

router = Router(name="menu")


async def render_view(
    message: types.Message,
    image_path: str,
    caption: str,
    keyboard: types.InlineKeyboardMarkup,
) -> bool:
    """统一渲染视图

    功能说明:
    - 始终编辑已有主消息以更新图片、说明与键盘

    输入参数:
    - message: Telegram消息对象
    - image_path: 图片路径
    - caption: 文本说明
    - keyboard: 内联键盘

    返回值:
    - bool: 是否成功编辑了主消息
    """
    p = Path(image_path)
    if p.exists():
        file = FSInputFile(str(p))
        media = InputMediaPhoto(media=file, caption=caption)
        with contextlib.suppress(Exception):
            await message.edit_media(media=media, reply_markup=keyboard)
            return True
        with contextlib.suppress(Exception):
            await message.edit_caption(caption, reply_markup=keyboard)
            return True
    with contextlib.suppress(Exception):
        await message.edit_text(text=caption, reply_markup=keyboard)
        return True
    return False


@router.message(Command(commands=["menu", "main"]))
async def menu_handler(message: types.Message) -> None:
    """主菜单处理器

    功能说明:
    - 显示基础主菜单

    输入参数:
    - message: Telegram消息对象

    返回值:
    - None
    """
    await message.answer("主菜单", reply_markup=main_keyboard())
