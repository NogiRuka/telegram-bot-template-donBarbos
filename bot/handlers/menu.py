from pathlib import Path

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto, FSInputFile

from bot.keyboards.inline.menu import main_keyboard

router = Router(name="menu")


async def render_view(message: types.Message, image_path: str, caption: str, keyboard: types.InlineKeyboardMarkup) -> None:
    """统一渲染视图

    功能说明:
    - 首次发送图片并设置说明与键盘
    - 后续通过编辑 caption 与键盘实现界面更新

    输入参数:
    - message: Telegram消息对象
    - image_path: 图片路径
    - caption: 文本说明
    - keyboard: 内联键盘

    返回值:
    - None
    """
    try:
        p = Path(image_path)
        if p.exists():
            try:
                file = FSInputFile(str(p))
                media = InputMediaPhoto(media=file, caption=caption)
                await message.edit_media(media=media, reply_markup=keyboard)
            except Exception:
                file = FSInputFile(str(p))
                await message.answer_photo(photo=file, caption=caption, reply_markup=keyboard)
        else:
            await message.answer(caption, reply_markup=keyboard)
    except Exception:
        await message.answer(caption, reply_markup=keyboard)


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
