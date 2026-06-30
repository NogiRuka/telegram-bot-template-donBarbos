from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.command._meta import collect_command_meta
from bot.handlers.command._usage import render_usage_lines
from bot.services.config_service import is_command_enabled
from bot.services.users import is_admin
from bot.utils.permissions import _resolve_role

router = Router(name="help")

COMMAND_META = {
    "name": "help",
    "alias": "h",
    "usage": "/h",
    "desc": "显示根据权限生成的命令帮助列表",
}


async def _append_scope_commands(
    lines: list[str],
    cmds: list[dict[str, object]],
    session: AsyncSession,
    scope: str,
) -> None:
    for cmd in cmds:
        name = str(cmd.get("name") or "")
        alias = str(cmd.get("alias") or "")
        desc = str(cmd.get("desc") or "")
        if not name and not alias:
            continue
        if scope in {"user", "admin"} and not await is_command_enabled(session, scope, name or alias):
            continue
        main_cmd = name or alias
        display = f"/{main_cmd} (/{alias})" if alias and alias != name else f"/{main_cmd}"
        lines.append(f"- {display} - {desc}")
        usage_lines = render_usage_lines(cmd)
        if usage_lines:
            lines.append("  用法:")
            lines.extend(usage_lines)


@router.message(Command("help", "h"))
async def help_command(message: types.Message, session: AsyncSession) -> None:
    user_cmds = collect_command_meta("bot.handlers.command.user")
    admin_cmds = collect_command_meta("bot.handlers.command.admin")
    owner_cmds = collect_command_meta("bot.handlers.command.owner")

    lines: list[str] = ["可用命令列表", "", "用户命令"]
    await _append_scope_commands(lines, user_cmds, session, "user")

    if message.from_user and await is_admin(session, message.from_user.id):
        lines.extend(["", "管理命令"])
        await _append_scope_commands(lines, admin_cmds, session, "admin")

    if message.from_user and await _resolve_role(session, message.from_user.id) == "owner":
        lines.extend(["", "所有者命令"])
        await _append_scope_commands(lines, owner_cmds, session, "owner")

    await message.reply("\n".join(lines), parse_mode=None)
