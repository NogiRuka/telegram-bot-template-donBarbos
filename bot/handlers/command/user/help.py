from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.command._meta import collect_command_meta
from bot.services.config_service import is_command_enabled
from bot.services.users import is_admin
from bot.utils.permissions import _resolve_role

router = Router(name="help")

COMMAND_META = {
    "name": "help",
    "alias": "h",
    "usage": "/help 或 /h",
    "desc": "显示根据权限生成的命令帮助列表"
}


@router.message(Command("help", "h"))
async def help_command(message: types.Message, session: AsyncSession) -> None:
    user_cmds = collect_command_meta("bot.handlers.command.user")
    admin_cmds = collect_command_meta("bot.handlers.command.admin")
    owner_cmds = collect_command_meta("bot.handlers.command.owner")

    text = "📜 可用命令列表\n\n👤 用户命令\n"

    for cmd in user_cmds:
        name = cmd.get("name") or ""
        alias = cmd.get("alias") or ""
        usage = cmd.get("usage") or ""
        desc = cmd.get("desc") or ""
        if not name and not alias:
            continue
        if not await is_command_enabled(session, "user", name or alias):
            continue
        main_cmd = name or alias
        display = f"/{main_cmd} (/{alias})" if alias and alias != name else f"/{main_cmd}"
        text += f"• {display} - {desc}\n"
        if usage:
            text += f"  用法: {usage}\n"

    if message.from_user and await is_admin(session, message.from_user.id):
        text += "\n👮 管理命令\n"
        for cmd in admin_cmds:
            name = cmd.get("name") or ""
            alias = cmd.get("alias") or ""
            usage = cmd.get("usage") or ""
            desc = cmd.get("desc") or ""
            if not name and not alias:
                continue
            if not await is_command_enabled(session, "admin", name or alias):
                continue
            main_cmd = name or alias
            display = f"/{main_cmd} (/{alias})" if alias and alias != name else f"/{main_cmd}"
            text += f"• {display} - {desc}\n"
            if usage:
                text += f"  用法: {usage}\n"

    if message.from_user and await _resolve_role(session, message.from_user.id) == "owner":
        text += "\n👑 所有者命令\n"
        for cmd in owner_cmds:
            name = cmd.get("name") or ""
            alias = cmd.get("alias") or ""
            usage = cmd.get("usage") or ""
            desc = cmd.get("desc") or ""
            if not name and not alias:
                continue
            main_cmd = name or alias
            display = f"/{main_cmd} (/{alias})" if alias and alias != name else f"/{main_cmd}"
            text += f"• {display} - {desc}\n"
            if usage:
                text += f"  用法: {usage}\n"

    await message.reply(text, parse_mode=None)
