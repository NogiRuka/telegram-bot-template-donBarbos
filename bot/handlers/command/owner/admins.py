"""所有者使用命令管理机器人管理员。"""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserExtendModel, UserModel, UserRole
from bot.services.users import add_admin, remove_admin
from bot.utils.permissions import require_owner
from bot.utils.text import build_user_link_html

router = Router(name="owner_admin_commands")

COMMAND_META = {
    "name": "admin",
    "alias": "a",
    "usage": "/admin <g|r|l> [用户ID|@用户名]",
    "desc": "管理机器人管理员",
}

GRANT_ACTIONS = {"g", "grant", "add", "添加"}
REVOKE_ACTIONS = {"r", "revoke", "remove", "移除"}
LIST_ACTIONS = {"l", "list", "列表"}


def _normalize_command_args(raw_args: str | None) -> list[str]:
    """规范化命令参数，并兼容动作与用户名连写。"""
    if not raw_args:
        return []
    args = raw_args.replace("\\@", "@").split()
    if not args:
        return []

    first = args[0].lower()
    target_actions = sorted(GRANT_ACTIONS | REVOKE_ACTIONS, key=len, reverse=True)
    for action in target_actions:
        compact_prefix = f"{action}@"
        if first.startswith(compact_prefix):
            target = first[len(action) :]
            return [action, target, *args[1:]]
    return args


async def _resolve_target_user(
    message: Message,
    raw_target: str | None,
    session: AsyncSession,
) -> tuple[int, User | UserModel | None] | None:
    """从回复消息、Telegram ID 或已记录用户名解析目标用户。"""
    if not raw_target:
        if message.reply_to_message and message.reply_to_message.from_user:
            user = message.reply_to_message.from_user
            return user.id, user
        return None

    target = raw_target.strip()
    if target.lstrip("-").isdigit():
        user_id = int(target)
        return user_id, await session.get(UserModel, user_id)
    if target.startswith("@") and len(target) > 1:
        username = target[1:]
        stmt = (
            select(UserModel)
            .where(func.lower(UserModel.username) == username.lower())
            .order_by(UserModel.updated_at.desc())
            .limit(1)
        )
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user:
            return user.id, user
    return None


async def _get_role(session: AsyncSession, user_id: int) -> UserRole | None:
    stmt = select(UserExtendModel.role).where(UserExtendModel.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


def _format_user_link(user_id: int, user: User | UserModel | None) -> str:
    """格式化可点击的用户姓名。"""
    first_name = user.first_name if user else "未知用户"
    last_name = user.last_name if user else None
    return build_user_link_html(user_id, first_name, last_name)


async def _format_admin_list(session: AsyncSession) -> str:
    """生成当前机器人管理员列表。"""
    stmt = (
        select(UserExtendModel.user_id)
        .where(UserExtendModel.role == UserRole.admin)
        .order_by(UserExtendModel.user_id)
    )
    user_ids = list((await session.execute(stmt)).scalars().all())
    if not user_ids:
        return "当前没有机器人管理员。"

    users_stmt = select(UserModel).where(UserModel.id.in_(user_ids))
    users = {
        user.id: user for user in (await session.execute(users_stmt)).scalars().all()
    }
    lines = ["当前机器人管理员："]
    for user_id in user_ids:
        lines.append(f"• {_format_user_link(user_id, users.get(user_id))}")
    return "\n".join(lines)


async def _change_admin_role(
    message: Message,
    session: AsyncSession,
    target_user_id: int,
    target_user: User | UserModel | None,
    *,
    grant: bool,
) -> None:
    """授予或撤销机器人管理员角色。"""
    role = await _get_role(session, target_user_id)
    user_link = _format_user_link(target_user_id, target_user)

    if role == UserRole.owner:
        await message.reply("❌ 不能修改机器人所有者的角色。")
        return
    if target_user and target_user.is_bot:
        await message.reply("❌ 不能把机器人账号设为管理员。")
        return
    if target_user is None:
        await message.reply(
            "❌ 找不到该用户，请让用户先与机器人交互，或回复该用户的消息。"
        )
        return

    operator_id = message.from_user.id if message.from_user else None
    if grant:
        if role == UserRole.admin:
            await message.reply(
                f"ℹ️ {user_link} 已经是机器人管理员。",
                parse_mode="HTML",
            )
            return
        success = await add_admin(session, target_user_id, operator_id=operator_id)
        result_text = f"✅ 已将 {user_link} 设为机器人管理员。"
    else:
        if role != UserRole.admin:
            await message.reply(
                f"ℹ️ {user_link} 当前不是机器人管理员。",
                parse_mode="HTML",
            )
            return
        success = await remove_admin(session, target_user_id, operator_id=operator_id)
        result_text = f"✅ 已撤销 {user_link} 的机器人管理员权限。"

    if not success:
        await message.reply("❌ 管理员角色更新失败，请查看日志。")
        return
    await message.reply(result_text, parse_mode="HTML")


@router.message(Command(COMMAND_META["name"], COMMAND_META["alias"]))
@require_owner
async def admin_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
) -> None:
    """处理机器人管理员的授予、撤销和列表查询。"""
    args = _normalize_command_args(command.args)
    action = args[0].lower() if args else None

    if action in LIST_ACTIONS:
        await message.reply(await _format_admin_list(session), parse_mode="HTML")
        return
    if action not in GRANT_ACTIONS | REVOKE_ACTIONS:
        await message.reply(
            "用法：`/admin g <用户>`、`/admin r <用户>`、`/admin l`；"
            "也可以回复用户消息后发送 `/admin g` 或 `/admin r`。",
            parse_mode="Markdown",
        )
        return

    target = await _resolve_target_user(
        message,
        args[1] if len(args) > 1 else None,
        session,
    )
    if target is None:
        await message.reply(
            "❌ 无法识别目标用户，请使用用户 ID、@用户名或回复用户消息。"
        )
        return
    await _change_admin_role(
        message,
        session,
        target[0],
        target[1],
        grant=action in GRANT_ACTIONS,
    )
