from aiogram import Router, types
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models import CommandPermissionScope
from bot.handlers.command._meta import collect_command_meta
from bot.services.command_permission_service import has_command_permission
from bot.utils.permissions import _resolve_role

router = Router(name="help")

COMMAND_META = {
    "name": "help",
    "alias": "h",
    "usage": "/h",
    "desc": "获取帮助",
}


def _append_commands(
    lines: list[str],
    cmds: list[dict[str, object]],
) -> None:
    for cmd in cmds:
        name = str(cmd.get("name") or "")
        alias = str(cmd.get("alias") or "")
        desc = str(cmd.get("desc") or "")
        if not name and not alias:
            continue
        lines.append(f"/{name or alias} {desc}")


async def _resolve_group_chat_id(message: types.Message) -> int | None:
    """解析帮助命令对应的群组；私聊时使用配置的主群。"""
    if message.chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return message.chat.id
    if message.chat.type != ChatType.PRIVATE or not settings.GROUP:
        return None
    try:
        chat = await message.bot.get_chat(settings.GROUP)
    except Exception:  # noqa: BLE001
        return None
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return None
    return chat.id


async def _is_group_admin(
    message: types.Message,
    user_id: int,
    chat_id: int,
) -> bool:
    """检查用户是否为指定群的管理员或群主。"""
    try:
        member = await message.bot.get_chat_member(chat_id, user_id)
    except Exception:  # noqa: BLE001
        return False
    return member.status in {
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }


async def _append_group_commands(
    lines: list[str],
    admin_cmds: list[dict[str, object]],
    message: types.Message,
    session: AsyncSession,
    user_id: int,
) -> None:
    """按当前群权限追加 `/spam`、`/q` 和 `/qs`。"""
    group_chat_id = await _resolve_group_chat_id(message)
    if group_chat_id is None:
        return

    is_group_admin = await _is_group_admin(message, user_id, group_chat_id)
    can_use_spam = is_group_admin
    if not can_use_spam:
        can_use_spam = await has_command_permission(
            session=session,
            user_id=user_id,
            command_name="spam",
            scope_type=CommandPermissionScope.GROUP,
            scope_id=group_chat_id,
        )

    visible_names = set()
    if can_use_spam:
        visible_names.add("spam")
    if is_group_admin:
        visible_names.update({"quiz", "quizs"})
    if not visible_names:
        return

    group_cmds = [
        cmd for cmd in admin_cmds if str(cmd.get("name") or "") in visible_names
    ]
    if not group_cmds:
        return
    command_lines: list[str] = []
    _append_commands(command_lines, group_cmds)
    if command_lines:
        lines.extend(command_lines)


@router.message(Command("help", "h"))
async def help_command(message: types.Message, session: AsyncSession) -> None:
    user_cmds = collect_command_meta("bot.handlers.command.user")
    admin_cmds = collect_command_meta("bot.handlers.command.admin")
    owner_cmds = collect_command_meta("bot.handlers.command.owner")

    lines: list[str] = ["/help 获取帮助"]
    other_user_cmds = [
        cmd for cmd in user_cmds if str(cmd.get("name") or "") != "help"
    ]
    _append_commands(lines, other_user_cmds)

    if not message.from_user:
        await message.reply("\n".join(lines), parse_mode=None)
        return

    user_id = message.from_user.id
    role = await _resolve_role(session, user_id)
    await _append_group_commands(lines, admin_cmds, message, session, user_id)

    if role in {"admin", "owner"}:
        robot_admin_cmds = [
            cmd
            for cmd in admin_cmds
            if str(cmd.get("name") or "") not in {"spam", "quiz", "quizs"}
        ]
        robot_admin_lines: list[str] = []
        _append_commands(robot_admin_lines, robot_admin_cmds)
        if robot_admin_lines:
            lines.extend(robot_admin_lines)

    if role == "owner":
        owner_lines: list[str] = []
        _append_commands(owner_lines, owner_cmds)
        if owner_lines:
            lines.extend(owner_lines)

    await message.reply("\n".join(lines), parse_mode=None)
