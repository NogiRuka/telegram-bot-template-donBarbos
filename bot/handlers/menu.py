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
    - 显示美化后的主面板文案与内联菜单

    输入参数:
    - message: Telegram消息对象

    返回值:
    - None
    """
    caption = (
        "🎀 桜色服务助手 | 主面板\n\n"
        "欢迎使用, 本机器人为你提供便捷的账号与群组管理:\n\n"
        "• 账号中心: 注册、信息、线路、设备、密码\n"
        "• 群组工具: 消息保存与导出(管理员)\n"
        "• 管理功能: 权限配置与统计(管理员/所有者)\n\n"
        "提示: 若功能提示不可用, 可能是权限不足或全局开关关闭。\n"
        "当总开关关闭时, 仅所有者可操作。\n\n"
        "请选择下方菜单开始使用 ⬇️"
    )
    await message.answer(caption, reply_markup=main_keyboard(), parse_mode="Markdown")
