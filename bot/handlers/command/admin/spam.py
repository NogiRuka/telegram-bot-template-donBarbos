"""群组垃圾账号封禁与消息清理命令。"""

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, User
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models import (
    AuditLogModel,
    CommandPermissionScope,
    MessageModel,
    UserModel,
)
from bot.database.models.audit_log import ActionType
from bot.handlers.command._usage import build_usage_text
from bot.services.command_permission_service import (
    has_command_permission,
    list_command_permissions,
    set_command_permission,
)
from bot.services.moderation_context import (
    discard_moderation_action,
    register_moderation_action,
)
from bot.utils.message import delete_message_after_delay, safe_delete_message
from bot.utils.permissions import require_admin_command_access
from bot.utils.text import build_user_link_html

router = Router(name="command_spam")

COMMAND_META = {
    "name": "spam",
    "alias": "s",
    "usage": {
        "summary": [
            "封禁垃圾账号并清理其近期消息",
            "清理操作仅能在群组中执行",
        ],
        "formats": [
            "回复垃圾消息后发送 /spam",
            "/spam <用户ID|@用户名>",
            "/spam g <用户ID|@用户名>",
            "/spam r <用户ID|@用户名>",
            "/spam l",
            "回复用户消息后发送 /spam g 或 /spam r",
        ],
        "examples": [
            "/spam 123456789",
            "/s g @username",
            "/s r 123456789",
            "/s l",
        ],
    },
    "desc": "封禁垃圾账号并清理其近期消息",
}

GRANT_ACTIONS = {"g", "grant", "allow", "add", "授权"}
REVOKE_ACTIONS = {"r", "revoke", "deny", "remove", "撤权"}
LIST_ACTIONS = {"l", "list", "列表"}
MAX_DELETE_MESSAGES = 100


async def _is_chat_admin(message: Message, user_id: int, chat_id: int) -> bool:
    """检查用户是否为指定群的管理员或创建者。"""
    try:
        member = await message.bot.get_chat_member(chat_id, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"检查群管理员身份失败: chat_id={chat_id}, "
            f"user_id={user_id}, error={exc}"
        )
        return False
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


async def _resolve_permission_chat_id(message: Message) -> int | None:
    """解析权限管理目标群；私聊时使用配置的主群。"""
    if message.chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return message.chat.id
    if message.chat.type != ChatType.PRIVATE or not settings.GROUP:
        return None
    try:
        chat = await message.bot.get_chat(settings.GROUP)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"解析权限管理目标群失败: group={settings.GROUP}, error={exc}")
        return None
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return None
    return chat.id


async def _is_spam_operator(session: AsyncSession, chat_id: int, user_id: int) -> bool:
    """检查成员是否拥有当前群的垃圾消息处理授权。"""
    return await has_command_permission(
        session=session,
        user_id=user_id,
        command_name=COMMAND_META["name"],
        scope_type=CommandPermissionScope.GROUP,
        scope_id=chat_id,
    )


async def _resolve_target_user(
    message: Message,
    raw_target: str | None,
    session: AsyncSession,
    member_chat_id: int,
) -> tuple[int, User | None] | None:
    """从回复消息、数字 ID 或机器人已记录的用户名解析目标。"""
    if not raw_target:
        if message.reply_to_message and message.reply_to_message.from_user:
            user = message.reply_to_message.from_user
            return user.id, user
        return None
    raw_target = raw_target.strip()
    if raw_target.lstrip("-").isdigit():
        return int(raw_target), None
    if raw_target.startswith("@") and len(raw_target) > 1:
        username = raw_target[1:]
        stmt = (
            select(UserModel)
            .where(func.lower(UserModel.username) == username.lower())
            .order_by(UserModel.updated_at.desc())
            .limit(1)
        )
        user_model = (await session.execute(stmt)).scalar_one_or_none()
        if user_model:
            try:
                member = await message.bot.get_chat_member(member_chat_id, user_model.id)
            except Exception:  # noqa: BLE001
                return None
            current_username = member.user.username or ""
            if current_username.lower() == username.lower():
                return user_model.id, member.user
    return None


def _normalize_command_args(raw_args: str | None) -> list[str]:
    """规范化命令参数，并兼容动作与用户名连写。"""
    if not raw_args:
        return []
    args = raw_args.replace("\\@", "@").split()
    if not args:
        return []

    first = args[0].lower()
    permission_actions = sorted(GRANT_ACTIONS | REVOKE_ACTIONS, key=len, reverse=True)
    for permission_action in permission_actions:
        compact_prefix = f"{permission_action}@"
        if first.startswith(compact_prefix):
            target = first[len(permission_action) :]
            return [permission_action, target, *args[1:]]
    return args


def _is_explicit_target(raw_target: str) -> bool:
    """判断参数是否是明确的用户 ID 或用户名，防止错误命令触发封禁。"""
    return raw_target.lstrip("-").isdigit() or (
        raw_target.startswith("@") and len(raw_target) > 1
    )


async def _reply_with_command_cleanup(
    message: Message,
    text: str,
    parse_mode: str | None = None,
) -> None:
    """回复临时提示，并在五秒后同时删除提示和触发命令。"""
    result_message = await message.reply(text, parse_mode=parse_mode)
    delete_message_after_delay(result_message, delay=5)
    delete_message_after_delay(message, delay=5)


async def _set_operator_permission(
    message: Message,
    session: AsyncSession,
    target_user_id: int,
    enabled: bool,
    permission_chat_id: int,
) -> None:
    """授予或撤销当前群成员的垃圾消息处理权限。"""
    changed = await set_command_permission(
        session=session,
        user_id=target_user_id,
        command_name=COMMAND_META["name"],
        scope_type=CommandPermissionScope.GROUP,
        granted_by_user_id=message.from_user.id,
        enabled=enabled,
        scope_id=permission_chat_id,
    )
    if enabled:
        result_text = (
            f"✅ 已授予用户 {target_user_id} `/spam` 执行权限。"
            if changed
            else f"ℹ️ 用户 {target_user_id} 已有 `/spam` 执行权限。"
        )
    else:
        result_text = (
            f"✅ 已撤销用户 {target_user_id} 的 `/spam` 执行权限。"
            if changed
            else f"ℹ️ 用户 {target_user_id} 当前没有 `/spam` 执行权限。"
        )

    await session.commit()
    result_message = await message.reply(result_text, parse_mode="Markdown")
    delete_message_after_delay(result_message, delay=5)
    delete_message_after_delay(message, delay=5)


async def _format_authorized_users(
    message: Message,
    session: AsyncSession,
    user_ids: list[int],
    permission_chat_id: int,
) -> str:
    """将授权用户格式化为可点击姓名链接。"""
    if not user_ids:
        return "当前没有已授权成员。"

    stmt = select(UserModel).where(UserModel.id.in_(user_ids))
    users = {user.id: user for user in (await session.execute(stmt)).scalars().all()}
    lines = ["当前已授权成员："]
    for user_id in user_ids:
        try:
            member = await message.bot.get_chat_member(permission_chat_id, user_id)
            first_name = member.user.first_name
            last_name = member.user.last_name
        except Exception as exc:  # noqa: BLE001
            logger.info(
                f"获取授权成员最新资料失败，使用数据库资料: "
                f"chat_id={permission_chat_id}, user_id={user_id}, error={exc}"
            )
            user = users.get(user_id)
            first_name = user.first_name if user else "未知用户"
            last_name = user.last_name if user else None
        user_link = build_user_link_html(user_id, first_name, last_name)
        lines.append(f"• {user_link}")
    return "\n".join(lines)


async def _validate_permission_target(
    message: Message,
    target_user_id: int,
    permission_chat_id: int,
) -> str | None:
    """验证授权目标是当前群内可被授权的普通成员。"""
    if target_user_id == message.from_user.id:
        return "群管理员无需额外授权。"
    try:
        member = await message.bot.get_chat_member(permission_chat_id, target_user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"检查授权目标失败: chat_id={permission_chat_id}, "
            f"user_id={target_user_id}, error={exc}"
        )
        return "无法确认目标用户是当前群成员，请回复该成员的群消息后重试。"
    if member.user.is_bot:
        return "不能把 `/spam` 权限授予机器人账号；机器人之间不会接收彼此发送的群消息。"
    if member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
        return "群管理员无需额外授权。"
    if member.status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}:
        return "只能把 `/spam` 权限授予当前群成员。"
    return None


async def _delete_recent_messages(
    message: Message,
    session: AsyncSession,
    target_user_id: int,
) -> tuple[int, int]:
    """删除数据库中记录的目标用户近期消息，并返回成功数与尝试数。"""
    stmt = (
        select(MessageModel)
        .where(
            MessageModel.chat_id == message.chat.id,
            MessageModel.user_id == target_user_id,
            MessageModel.is_deleted.is_(False),
        )
        .order_by(MessageModel.message_id.desc())
        .limit(MAX_DELETE_MESSAGES)
    )
    records = list((await session.execute(stmt)).scalars().all())
    message_ids = {record.message_id for record in records}
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == target_user_id:
            message_ids.add(message.reply_to_message.message_id)

    deleted_ids: set[int] = set()
    if message_ids:
        try:
            await message.bot.delete_messages(
                chat_id=message.chat.id,
                message_ids=sorted(message_ids),
            )
            deleted_ids.update(message_ids)
        except Exception as exc:  # noqa: BLE001
            logger.info(
                f"批量删除垃圾消息失败，改为逐条处理: "
                f"chat_id={message.chat.id}, error={exc}"
            )
            for message_id in message_ids:
                if await safe_delete_message(message.bot, message.chat.id, message_id):
                    deleted_ids.add(message_id)

    for record in records:
        if record.message_id in deleted_ids:
            record.soft_delete()
            record.deleted_by = message.from_user.id
    return len(deleted_ids), len(message_ids)


async def _execute_spam_action(message: Message, session: AsyncSession, target_user_id: int) -> None:
    """封禁目标账号并清理其在当前群的近期消息。"""
    if target_user_id == message.from_user.id:
        await message.reply("❌ 不能对自己执行 `/spam`。", parse_mode="Markdown")
        return
    bot_user = await message.bot.me()
    if target_user_id == bot_user.id:
        await message.reply("❌ 不能对机器人自身执行 `/spam`。", parse_mode="Markdown")
        return
    if await _is_chat_admin(message, target_user_id, message.chat.id):
        await message.reply("❌ 不能通过 `/spam` 封禁群管理员或群主。", parse_mode="Markdown")
        return

    register_moderation_action(
        chat_id=message.chat.id,
        target_user_id=target_user_id,
        actor_user_id=message.from_user.id,
        actor_full_name=message.from_user.full_name,
        action="spam",
    )
    try:
        await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user_id)
    except Exception as exc:  # noqa: BLE001
        discard_moderation_action(message.chat.id, target_user_id)
        logger.warning(
            f"封禁垃圾账号失败: chat_id={message.chat.id}, "
            f"user_id={target_user_id}, error={exc}"
        )
        await message.reply(f"❌ 封禁失败，未继续清理消息：{exc}")
        return

    deleted_count, attempted_count = await _delete_recent_messages(message, session, target_user_id)
    session.add(
        AuditLogModel(
            operator_id=message.from_user.id,
            user_id=target_user_id,
            action_type=ActionType.USER_BLOCK,
            target_type="telegram_user",
            target_id=str(target_user_id),
            description=f"将用户 {target_user_id} 标记为垃圾账号并封禁",
            details={
                "chat_id": message.chat.id,
                "source": "spam_command",
                "deleted_messages": deleted_count,
                "attempted_messages": attempted_count,
            },
            user_agent="TelegramBot/spam-command",
        )
    )
    await session.commit()
    result_message = await message.reply(
        f"✅ 已封禁垃圾账号 {target_user_id}。\n"
        f"🧹 已删除 {deleted_count}/{attempted_count} 条可定位消息。"
    )
    delete_message_after_delay(result_message, delay=5)
    delete_message_after_delay(message, delay=5)


@router.message(Command("spam", "s"))
@require_admin_command_access(COMMAND_META["name"])
async def spam_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """处理垃圾账号封禁、消息清理及群级授权。"""
    if not message.from_user:
        return

    args = _normalize_command_args(command.args)
    action = args[0].lower() if args else None

    if not args and not (
        message.reply_to_message and message.reply_to_message.from_user
    ):
        await message.reply(build_usage_text(COMMAND_META), parse_mode="Markdown")
        return

    if action in GRANT_ACTIONS | REVOKE_ACTIONS | LIST_ACTIONS:
        permission_chat_id = await _resolve_permission_chat_id(message)
        if permission_chat_id is None:
            await message.reply("❌ 无法确定需要管理的群组。")
            return
        is_admin = await _is_chat_admin(
            message,
            message.from_user.id,
            permission_chat_id,
        )
        if not is_admin:
            await _reply_with_command_cleanup(message, "❌ 你没有权限执行此操作。")
            return
        if action in LIST_ACTIONS:
            user_ids = await list_command_permissions(
                session=session,
                command_name=COMMAND_META["name"],
                scope_type=CommandPermissionScope.GROUP,
                scope_id=permission_chat_id,
            )
            await _reply_with_command_cleanup(
                message,
                await _format_authorized_users(
                    message,
                    session,
                    user_ids,
                    permission_chat_id,
                ),
                parse_mode="HTML",
            )
            return
        target = await _resolve_target_user(
            message,
            args[1] if len(args) > 1 else None,
            session,
            permission_chat_id,
        )
        if target is None:
            await message.reply(build_usage_text(COMMAND_META), parse_mode="Markdown")
            return
        if action in GRANT_ACTIONS:
            validation_error = await _validate_permission_target(
                message,
                target[0],
                permission_chat_id,
            )
            if validation_error:
                await message.reply(validation_error, parse_mode="Markdown")
                return
        await _set_operator_permission(
            message,
            session,
            target[0],
            action in GRANT_ACTIONS,
            permission_chat_id,
        )
        return

    if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        await message.reply("❌ `/spam`（`/s`）清理操作只能在群组中使用。", parse_mode="Markdown")
        return

    is_admin = await _is_chat_admin(message, message.from_user.id, message.chat.id)
    if not is_admin and not await _is_spam_operator(session, message.chat.id, message.from_user.id):
        await _reply_with_command_cleanup(message, "❌ 你没有权限执行此操作。")
        return
    if args and not _is_explicit_target(args[0]):
        await message.reply(
            "❌ 无法识别参数，未执行封禁。\n"
            f"\n{build_usage_text(COMMAND_META)}",
            parse_mode="Markdown",
        )
        return
    target = await _resolve_target_user(
        message,
        args[0] if args else None,
        session,
        message.chat.id,
    )
    if target is None:
        await message.reply(build_usage_text(COMMAND_META), parse_mode="Markdown")
        return
    await _execute_spam_action(message, session, target[0])
