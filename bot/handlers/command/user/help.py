from aiogram import Router, types
from aiogram.filters import Command
from aiogram.filters.command import Command as CommandFilter
from sqlalchemy.ext.asyncio import AsyncSession
import importlib
import pkgutil
from typing import Iterable

from bot.services.users import is_admin

router = Router(name="help")

COMMAND_META = {
    "name": "c",
    "alias": "help",
    "usage": "/c",
    "desc": "显示根据权限生成的命令帮助列表"
}


def _escape_mdv2(text: str) -> str:
    specials = r"_\*[]()~`>#+-=|{}.!<>"
    out = []
    for ch in text:
        if ch in specials:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


@router.message(Command("c"))
async def help_command(message: types.Message, session: AsyncSession):

    user_cmds = []
    user_cmds.extend(_collect_command_meta("bot.handlers.command.common"))
    user_cmds.extend(_collect_command_meta("bot.handlers.command.user"))

    admin_cmds = _collect_command_meta("bot.handlers.command.admin")

    text = "📜 *可用命令列表*\n\n👤 *用户命令*\n"

    for cmd in user_cmds:

        alias = cmd.get("alias")
        usage = cmd.get("usage")
        desc  = cmd.get("desc")

        text += f"• {_escape_mdv2('/' + alias)} - {_escape_mdv2(desc)}\n"
        text += f"  {_escape_mdv2('用法: ' + usage)}\n"

    if message.from_user and await is_admin(session, message.from_user.id):

        text += "\n👮 *管理命令*\n"

        for cmd in admin_cmds:

            alias = cmd.get("alias")
            usage = cmd.get("usage")
            desc  = cmd.get("desc")

            text += f"• {_escape_mdv2('/' + alias)} - {_escape_mdv2(desc)}\n"
            text += f"  {_escape_mdv2('用法: ' + usage)}\n"

    await message.reply(text, parse_mode="MarkdownV2")