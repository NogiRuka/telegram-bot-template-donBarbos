"""
禁用 Emby 用户命令模块
"""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.command._usage import build_usage_text
from bot.services.admin_service import disable_emby_user
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import require_admin_command_access, require_admin_priv

router = Router(name="command_disable_user")

COMMAND_META = {
    "name": "disable_user",
    "alias": "du",
    "usage": "/du <user_id|emby_id> [原因]",
    "example": {
        "command": "/du 123456789 违规分享",
        "explain": "禁用指定用户Emby账号，并记录原因“违规分享”",
    },
    "desc": "禁用 Emby 账号",
}


@router.message(Command("disable_user", "du"))
@private_chat_only
@require_admin_priv
@require_admin_command_access(COMMAND_META["name"])
async def disable_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not command.args:
        await message.reply(build_usage_text(COMMAND_META), parse_mode="Markdown")
        return

    args = command.args.split(maxsplit=1)
    target_id = args[0].strip()
    reason = args[1].strip() if len(args) > 1 else "管理员手动禁用"

    if not target_id.isalnum():
        await message.reply("无效的 ID 格式。")
        return

    results = await disable_emby_user(
        session=session,
        target_id=target_id,
        admin_id=message.from_user.id,
        reason=reason,
        bot=message.bot,
        user_info={"action": "ManualDisable", "target": target_id},
    )

    await message.reply("\n".join(results))
