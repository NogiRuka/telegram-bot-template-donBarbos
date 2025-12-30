from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.media_file import MediaFileModel
from bot.utils.text import escape_markdown_v2

router = Router(name="user_files")


@router.message(Command(commands=["get_file", "gf"]))
async def get_file_command(message: Message, session: AsyncSession) -> None:
    """获取文件命令

    功能说明:
    - 通过 /get_file <unique_name> 或 <file_unique_id> 获取文件
    - 优先匹配 unique_name，其次匹配 file_unique_id
    - 返回单个文件

    输入参数:
    - message: 消息对象
    - session: 数据库会话

    返回值:
    - None
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ 请提供文件名或ID\n用法: `/get_file <unique_name>` 或 `/gf <unique_name>`", parse_mode="MarkdownV2")
        return

    search_term = args[1].strip()
    
    # 优先搜索 unique_name
    stmt = select(MediaFileModel).where(MediaFileModel.unique_name == search_term, MediaFileModel.is_deleted.is_(False))
    file_record = (await session.execute(stmt)).scalar_one_or_none()

    # 如果没找到，尝试搜索 file_unique_id
    if not file_record:
        stmt = select(MediaFileModel).where(MediaFileModel.file_unique_id == search_term, MediaFileModel.is_deleted.is_(False))
        file_record = (await session.execute(stmt)).scalar_one_or_none()

    if not file_record:
        await message.reply(f"❌ 未找到文件: `{escape_markdown_v2(search_term)}`", parse_mode="MarkdownV2")
        return

    try:
        caption = (
            f"📄 *文件名*: `{escape_markdown_v2(file_record.file_name or '-')}`\n"
            f"🔖 *唯一名*: `{escape_markdown_v2(file_record.unique_name or '-')}`\n"
            f"🏷️ *类型*: {escape_markdown_v2(file_record.media_type)}\n"
            f"📛 *标签*: {escape_markdown_v2(file_record.label or '-')}"
        )

        if file_record.media_type == "photo":
            await message.answer_photo(photo=file_record.file_id, caption=caption, parse_mode="MarkdownV2")
        elif file_record.media_type == "document":
            await message.answer_document(document=file_record.file_id, caption=caption, parse_mode="MarkdownV2")
        elif file_record.media_type == "video":
            await message.answer_video(video=file_record.file_id, caption=caption, parse_mode="MarkdownV2")
        elif file_record.media_type == "audio":
            await message.answer_audio(audio=file_record.file_id, caption=caption, parse_mode="MarkdownV2")
        elif file_record.media_type == "voice":
            await message.answer_voice(voice=file_record.file_id, caption=caption, parse_mode="MarkdownV2")
        elif file_record.media_type == "animation":
            await message.answer_animation(animation=file_record.file_id, caption=caption, parse_mode="MarkdownV2")
        elif file_record.media_type == "sticker":
            await message.answer_sticker(sticker=file_record.file_id)
            await message.answer(caption, parse_mode="MarkdownV2")
        elif file_record.media_type == "video_note":
            await message.answer_video_note(video_note=file_record.file_id)
            await message.answer(caption, parse_mode="MarkdownV2")
        else:
            await message.answer(f"📦 文件ID: `{file_record.file_id}`\n(不支持的媒体类型)", parse_mode="MarkdownV2")

    except Exception as e:
        await message.answer(f"❌ 发送文件失败: {e}")
