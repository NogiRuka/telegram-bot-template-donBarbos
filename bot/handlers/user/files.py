from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import re

from bot.database.models.media_file import MediaFileModel
from bot.utils.text import escape_markdown_v2

router = Router(name="user_files")


async def search_and_send_file(message: Message, session: AsyncSession, search_term: str) -> None:
    """搜索并发送文件通用逻辑"""
    if not search_term:
        await message.reply("⚠️ 请提供文件名或ID\n用法: `/get_file <unique_name>` 或 `/gf <unique_name>`", parse_mode="MarkdownV2")
        return

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
            f"🔖 *唯一名*: `{escape_markdown_v2(file_record.unique_name)}`\n"
            f"🏷️ *类型*: {escape_markdown_v2(file_record.media_type)}"
        )
        if file_record.description:
            caption += f"\n📛 *说明*: {escape_markdown_v2(file_record.description)}"

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
            await message.reply(f"📦 文件ID: `{file_record.file_id}`\n(不支持的媒体类型)", parse_mode="MarkdownV2")

    except Exception as e:
        await message.reply(f"❌ 发送文件失败: {e}")


@router.message(Command(commands=["get_file", "gf"]))
async def get_file_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """获取文件命令 (标准格式)
    
    功能说明:
    - 处理 /get_file 或 /gf 命令
    - 支持 /gf <args> 和 /gf@bot <args>
    """
    args = command.args or ""
    terms = re.findall(r"\S+", args)
    if not terms:
        await search_and_send_file(message, session, "")
        return
    seen: set[str] = set()
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        await search_and_send_file(message, session, term)
