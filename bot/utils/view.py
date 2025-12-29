import contextlib
from pathlib import Path

from aiogram import Bot, types
from aiogram.types import FSInputFile, InputMediaPhoto


async def render_view(
    message: types.Message,
    caption: str,
    keyboard: types.InlineKeyboardMarkup,
    image_path: str | None = None,
) -> bool:
    """统一渲染视图
    
    功能说明:
    - 在单条主消息上进行编辑更新, 优先尝试编辑图片与说明, 其次仅编辑说明, 最后回退为编辑纯文本, 保持对话整洁.
    - 异步调用方式: 使用 `await` 调用本函数; 内部使用 Telegram API 的 `edit_media`, `edit_caption`, `edit_text`.
    
    输入参数:
    - message: Telegram消息对象(aiogram 的 `types.Message`)
    - caption: 文本说明内容, 建议不超过 Telegram caption 长度限制
    - keyboard: 内联键盘(`types.InlineKeyboardMarkup`)
    - image_path: 图片绝对/相对路径, 存在时优先编辑为图片消息
    
    返回值:
    - bool: 是否成功编辑了主消息
    
    依赖:
    - aiogram(安装: `pip install aiogram`)
    
    Telegram API 限制:
    - 文本/Caption 长度约上限 4096 字符; 过长需截断或分条发送
    - 频繁编辑可能触发限流, 需注意操作节奏
    """
    p = Path(image_path) if image_path else None
    image_exists = p.exists() if p else False
    # 仅当原消息为媒体消息时才尝试编辑媒体, 否则直接编辑文本
    is_media_message = bool(
        getattr(message, "photo", None)
        or getattr(message, "video", None)
        or getattr(message, "animation", None)
        or getattr(message, "document", None)
    )

    async def _try_sequence(ops: list) -> bool:
        """依次尝试编辑操作, 成功即返回 True, 全部失败返回 False"""
        for op in ops:
            with contextlib.suppress(Exception):
                await op()
                return True
        return False

    success = False
    if image_exists and is_media_message and p:
        file = FSInputFile(str(p))
        async def op_media_md() -> None:
            media_obj = InputMediaPhoto(media=file, caption=caption, parse_mode="MarkdownV2")
            await message.edit_media(media=media_obj, reply_markup=keyboard)
        async def op_media_plain() -> None:
            await message.edit_media(media=InputMediaPhoto(media=file, caption=caption), reply_markup=keyboard)
        async def op_caption_md() -> None:
            await message.edit_caption(caption, reply_markup=keyboard, parse_mode="MarkdownV2")
        async def op_caption_plain() -> None:
            await message.edit_caption(caption, reply_markup=keyboard)
        success = await _try_sequence([op_media_md, op_media_plain, op_caption_md, op_caption_plain])
    else:
        async def op_text_md() -> None:
            await message.edit_text(text=caption, reply_markup=keyboard, parse_mode="MarkdownV2")
        async def op_text_plain() -> None:
            await message.edit_text(text=caption, reply_markup=keyboard)
        success = await _try_sequence([op_text_md, op_text_plain])
    return success


async def edit_message_content(
    message: types.Message,
    caption: str,
    keyboard: types.InlineKeyboardMarkup,
) -> bool:
    """编辑消息内容(通用)

    功能说明:
    - 通用编辑入口, 优先尝试编辑消息的 caption 与键盘; 当消息为纯文本时回退为编辑文本与键盘

    输入参数:
    - message: Telegram 消息对象
    - caption: 文本说明内容
    - keyboard: 内联键盘

    返回值:
    - bool: 是否成功编辑
    """
    with contextlib.suppress(Exception):
        await message.edit_caption(caption, reply_markup=keyboard)
        return True
    with contextlib.suppress(Exception):
        await message.edit_text(text=caption, reply_markup=keyboard)
        return True
    return False


async def edit_message_content_by_id(
    bot: Bot,
    chat_id: int,
    message_id: int,
    caption: str,
    keyboard: types.InlineKeyboardMarkup,
) -> bool:
    """按消息ID编辑消息内容(通用)

    功能说明:
    - 通用编辑入口(基于 chat_id 与 message_id), 优先尝试编辑 caption 与键盘; 失败回退为编辑文本与键盘

    输入参数:
    - bot: Telegram Bot 对象
    - chat_id: 聊天 ID
    - message_id: 消息 ID
    - caption: 文本说明内容
    - keyboard: 内联键盘

    返回值:
    - bool: 是否成功编辑
    """
    with contextlib.suppress(Exception):
        await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=keyboard)
        return True
    with contextlib.suppress(Exception):
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=caption, reply_markup=keyboard)
        return True
    return False
