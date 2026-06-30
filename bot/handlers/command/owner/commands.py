from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.command._meta import collect_command_names
from bot.handlers.command._usage import build_usage_text
from bot.services.config_service import get_disabled_commands, toggle_command_access
from bot.utils.permissions import require_owner

router = Router(name="owner_commands")

COMMAND_META = {
    "name": "command",
    "alias": "c",
    "usage": "/c [user|admin] [name]",
    "example": {
        "command": "/c admin quiz",
        "explain": "切换管理员命令 quiz 的开关状态",
    },
    "desc": "查看或切换用户、管理员命令权限",
}


def _collect_command_names_by_scope(scope: str) -> list[str]:
    package = "bot.handlers.command.user" if scope == "user" else "bot.handlers.command.admin"
    return collect_command_names(package)


async def _format_commands_status(
    session: AsyncSession,
    scope: str,
    names: list[str],
) -> list[str]:
    disabled = await get_disabled_commands(session, scope)
    lines: list[str] = []
    title = "用户命令" if scope == "user" else "管理员命令"
    lines.append(f"{title}:")
    for name in names:
        enabled = name not in disabled
        status = "启用" if enabled else "禁用"
        lines.append(f"{status} {name}")
    return lines


@router.message(Command("command", "c"))
@require_owner
async def owner_command_control(message: Message, command: CommandObject, session: AsyncSession) -> None:
    args_raw = (command.args or "").strip()
    user_commands = _collect_command_names_by_scope("user")
    admin_commands = _collect_command_names_by_scope("admin")

    if not args_raw:
        parts: list[str] = []
        parts.append("命令权限")
        parts.append("")
        parts.extend(await _format_commands_status(session, "user", user_commands))
        parts.append("")
        parts.extend(await _format_commands_status(session, "admin", admin_commands))
        await message.reply("\n".join(parts), parse_mode=None)
        return

    parts = args_raw.split()
    scope = parts[0] if parts else ""
    name = parts[1] if len(parts) > 1 else ""

    if scope not in {"user", "admin"} or not name:
        await message.reply(build_usage_text(COMMAND_META), parse_mode="Markdown")
        return

    valid = name in user_commands if scope == "user" else name in admin_commands
    if not valid:
        await message.reply("无效的命令名。", parse_mode=None)
        return

    operator_id = message.from_user.id if message.from_user else None
    enabled = await toggle_command_access(session, scope, name, operator_id=operator_id)

    scope_label = "用户" if scope == "user" else "管理员"
    status = "启用" if enabled else "禁用"
    await message.reply(f"已{status}{scope_label}命令: {name}", parse_mode=None)
