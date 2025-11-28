import contextlib
from pathlib import Path

from aiogram import types
from aiogram.types import FSInputFile, InputMediaPhoto


async def render_view(
    message: types.Message,
    image_path: str,
    caption: str,
    keyboard: types.InlineKeyboardMarkup,
) -> bool:
    """统一渲染视图

    功能说明:
    - 在单条主消息上进行编辑更新，优先尝试编辑图片与说明，其次仅编辑说明，最后回退为编辑纯文本，保持对话整洁。
    - 异步调用方式：使用 `await` 调用本函数；内部使用 Telegram API 的 `edit_media`、`edit_caption`、`edit_text`。

    输入参数:
    - message: Telegram消息对象（aiogram 的 `types.Message`）
    - image_path: 图片绝对/相对路径，存在时优先编辑为图片消息
    - caption: 文本说明内容，建议不超过 Telegram caption 长度限制
    - keyboard: 内联键盘（`types.InlineKeyboardMarkup`）

    返回值:
    - bool: 是否成功编辑了主消息

    依赖:
    - aiogram（安装：`pip install aiogram`）

    Telegram API 限制:
    - 文本/Caption 长度约上限 4096 字符；过长需截断或分条发送
    - 频繁编辑可能触发限流，需注意操作节奏
    """
    p = Path(image_path)
    image_exists = p.exists()
    # 仅当原消息为媒体消息时才尝试编辑媒体，否则直接编辑文本
    is_media_message = bool(getattr(message, "photo", None) or getattr(message, "video", None) or getattr(message, "animation", None) or getattr(message, "document", None))

    if image_exists and is_media_message:
        file = FSInputFile(str(p))
        media = InputMediaPhoto(media=file, caption=caption, parse_mode="MarkdownV2")
        with contextlib.suppress(Exception):
            await message.edit_media(media=media, reply_markup=keyboard)
            return True
        media_plain = InputMediaPhoto(media=file, caption=caption)
        with contextlib.suppress(Exception):
            await message.edit_media(media=media_plain, reply_markup=keyboard)
            return True
        with contextlib.suppress(Exception):
            await message.edit_caption(caption, reply_markup=keyboard, parse_mode="MarkdownV2")
            return True
        with contextlib.suppress(Exception):
            await message.edit_caption(caption, reply_markup=keyboard)
            return True

    with contextlib.suppress(Exception):
        await message.edit_text(text=caption, reply_markup=keyboard, parse_mode="MarkdownV2")
        return True
    with contextlib.suppress(Exception):
        await message.edit_text(text=caption, reply_markup=keyboard)
        return True
    return False
