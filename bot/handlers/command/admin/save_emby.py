from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.emby_service import run_emby_sync
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import require_admin_priv

router = Router(name="command_save_emby")

COMMAND_META = {
    "name": "save_emby",
    "alias": "se",
    "usage": "/save_emby 或 /se",
    "desc": "手动触发 Emby 数据同步"
}

@router.message(Command("save_emby", "se"))
@private_chat_only
@require_admin_priv
async def save_emby_command(message: Message, session: AsyncSession) -> None:
    """
    手动触发 Emby 数据同步

    功能说明:
    - 管理员手动触发 Emby 用户和设备数据的同步
    - 这是一个耗时操作

    输入参数:
    - message: 消息对象
    - session: 数据库会话

    返回值:
    - None
    """
    status_msg = await message.reply("⏳ 正在同步 Emby 数据...")

    await run_emby_sync(session)

    await status_msg.edit_text("✅ Emby 数据同步完成")
