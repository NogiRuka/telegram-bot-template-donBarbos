"""
启用 Emby 用户命令模块
"""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.admin_service import enable_emby_user
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import require_admin_command_access, require_admin_priv

router = Router(name="command_enable_user")

COMMAND_META = {
    "name": "enable_user",
    "alias": "eu",
    "usage": "/enable_user <user_id_or_emby_id>",
    "desc": "启用 Emby 账号"
}


@router.message(Command("enable_user", "eu"))
@private_chat_only
@require_admin_priv
@require_admin_command_access(COMMAND_META["name"])
async def enable_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    启用 Emby 用户命令

    功能:
    1. 启用指定用户的 Emby 账号
    2. 记录审计日志

    用法: /enable_user <telegram_user_id 或 emby_user_id>
    """
    if not command.args:
        await message.reply(
            "⚠️ 请提供 Telegram 用户 ID 或 Emby 用户 ID\n"
            "用法: `/enable_user <user_id>`",
            parse_mode="Markdown"
        )
        return

    target_id = command.args.strip()
    
    # 简单的 ID 格式校验
    if not target_id.isalnum():
        await message.reply("❌ 无效的 ID 格式")
        return

    results = await enable_emby_user(
        session=session,
        target_id=target_id,
        admin_id=message.from_user.id,
        reason="管理员手动启用",
        bot=message.bot,
        user_info={"action": "ManualEnable", "target": target_id}
    )

    await message.reply("\n".join(results))
