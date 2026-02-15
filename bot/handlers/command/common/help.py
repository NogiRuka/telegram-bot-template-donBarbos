from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
import importlib
import pkgutil
from typing import Iterable

from bot.services.users import is_admin
from aiogram.filters.command import Command as CommandFilter

router = Router(name="help")


def _escape_mdv2(text: str) -> str:
    # Telegram MarkdownV2 需要转义的字符集
    specials = r"_\*[]()~`>#+-=|{}.!<>"
    out = []
    for ch in text:
        if ch in specials:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _extract_commands_from_router(router: Router) -> list[str]:
    cmds: list[str] = []
    try:
        for h in getattr(router.message, "handlers", []):
            for f in getattr(h, "filters", []):
                if isinstance(f, CommandFilter):
                    values: Iterable[str] | None = getattr(f, "commands", None)
                    if values:
                        for c in values:
                            if isinstance(c, str):
                                cmds.append(c)
    except Exception:
        pass
    return sorted(set(cmds))


def _collect_command_names(package: str) -> list[str]:
    cmds: list[str] = []
    try:
        pkg = importlib.import_module(package)
        for m in pkgutil.iter_modules(pkg.__path__, package + "."):
            mod = importlib.import_module(m.name)
            r = getattr(mod, "router", None)
            if isinstance(r, Router):
                cmds.extend(_extract_commands_from_router(r))
    except Exception:
        pass
    return sorted(set(cmds))


@router.message(Command("c"))
async def help_command(message: types.Message, session: AsyncSession) -> None:
    """
    帮助命令（动态生成）
    """
    user_cmds = []
    user_cmds.extend(_collect_command_names("bot.handlers.command.common"))
    user_cmds.extend(_collect_command_names("bot.handlers.command.user"))
    admin_cmds = _collect_command_names("bot.handlers.command.admin")

    text = "📜 *可用命令列表*\n👤 *用户命令*\n"
    base = ["/start", "/help", "/info", "/gf <唯一名>", "/c"]
    text += "\n".join(f"• {_escape_mdv2(line)}" for line in base) + "\n"

    for cmd in sorted(set(user_cmds)):
        if cmd not in {"c"}:
            text += f"• {_escape_mdv2('/' + cmd)}\n"

    if message.from_user and await is_admin(session, message.from_user.id):
        text += "\n👮 *管理命令*\n"
        for cmd in admin_cmds:
            text += f"• {_escape_mdv2('/' + cmd)}\n"

    await message.reply(text, parse_mode="MarkdownV2")
