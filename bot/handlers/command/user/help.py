import importlib
import pkgutil
from typing import Iterable

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.users import is_admin
from bot.core.config import settings
from bot.services.config_service import is_command_enabled

router = Router(name="help")

COMMAND_META = {
    "name": "help",
    "alias": "h",
    "usage": "/help 或 /h",
    "desc": "显示根据权限生成的命令帮助列表"
}


def _collect_command_meta(package: str) -> list[dict]:
    metas: list[dict] = []
    try:
        pkg = importlib.import_module(package)
        for m in pkgutil.iter_modules(pkg.__path__, package + "."):
            mod = importlib.import_module(m.name)
            meta = getattr(mod, "COMMAND_META", None)
            if isinstance(meta, dict):
                metas.append(meta)
    except Exception:
        pass
    return metas


@router.message(Command("help", "h"))
async def help_command(message: types.Message, session: AsyncSession) -> None:
    user_cmds = _collect_command_meta("bot.handlers.command.user")
    admin_cmds = _collect_command_meta("bot.handlers.command.admin")
    owner_cmds = _collect_command_meta("bot.handlers.command.owner")

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
        if alias and alias != name:
            display = f"/{main_cmd} (/{alias})"
        else:
            display = f"/{main_cmd}"
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
            if alias and alias != name:
                display = f"/{main_cmd} (/{alias})"
            else:
                display = f"/{main_cmd}"
            text += f"• {display} - {desc}\n"
            if usage:
                text += f"  用法: {usage}\n"

    if message.from_user and message.from_user.id == settings.get_owner_id():
        text += "\n👑 所有者命令\n"
        for cmd in owner_cmds:
            name = cmd.get("name") or ""
            alias = cmd.get("alias") or ""
            usage = cmd.get("usage") or ""
            desc = cmd.get("desc") or ""
            if not name and not alias:
                continue
            main_cmd = name or alias
            if alias and alias != name:
                display = f"/{main_cmd} (/{alias})"
            else:
                display = f"/{main_cmd}"
            text += f"• {display} - {desc}\n"
            if usage:
                text += f"  用法: {usage}\n"

    await message.reply(text, parse_mode=None)
