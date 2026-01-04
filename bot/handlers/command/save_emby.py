from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.emby_service import run_emby_sync
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import require_admin_priv

router = Router(name="command_save_emby")

@router.message(Command("save_emby", "se"))
@private_chat_only
@require_admin_priv
async def save_emby_command(message: Message, session: AsyncSession) -> None:
    """
    手动触发 Emby 数据同步
    """
    status_msg = await message.reply("⏳ 正在同步 Emby 数据...")

    await run_emby_sync(session)

    await status_msg.edit_text("✅ Emby 数据同步完成")
