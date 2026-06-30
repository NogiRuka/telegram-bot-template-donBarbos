"""
封禁用户命令模块
"""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models import UserModel
from bot.handlers.command._usage import build_usage_text
from bot.services.admin_service import ban_emby_user
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import require_admin_command_access, require_admin_priv
from bot.utils.text import escape_markdown_v2

router = Router(name="command_ban")

COMMAND_META = {
    "name": "ban",
    "alias": "b",
    "usage": "/b <user_id>",
    "example": {
        "command": "/b 123456789",
        "explain": "封禁 Telegram 用户 123456789",
    },
    "desc": "封禁用户",
}


@router.message(Command("ban", "b"))
@private_chat_only
@require_admin_priv
@require_admin_command_access(COMMAND_META["name"])
async def ban_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not command.args:
        await message.reply(build_usage_text(COMMAND_META), parse_mode="Markdown")
        return

    try:
        target_user_id = int(command.args)
    except ValueError:
        await message.reply("无效的用户 ID，必须为整数。")
        return

    results: list[str] = []

    if settings.GROUP:
        try:
            await message.bot.ban_chat_member(chat_id=settings.GROUP, user_id=target_user_id)
            results.append("已从群组移除并封禁。")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"无法从群组移除用户 {target_user_id}: {exc}")
            safe_error = escape_markdown_v2(str(exc))
            results.append(f"无法从群组移除: {safe_error}")
    else:
        results.append("未配置群组，已跳过群组封禁。")

    group_name = "Private"
    chat_id = None
    chat_username = None

    if message.chat.type != "private":
        group_name = message.chat.title or "Unknown"
        chat_id = message.chat.id
        chat_username = message.chat.username
    elif settings.GROUP:
        group_name = f"Group{settings.GROUP}"
        try:
            chat_id = int(settings.GROUP)
        except (ValueError, TypeError):
            chat_username = settings.GROUP

    db_user = (await session.execute(select(UserModel).where(UserModel.id == target_user_id))).scalar_one_or_none()
    if db_user:
        user_info = {
            "group_name": group_name,
            "chat_id": chat_id,
            "chat_username": chat_username,
            "username": db_user.username or "",
            "full_name": db_user.get_full_name(),
            "action": "ManualBan",
            "user_id": str(target_user_id),
        }
    else:
        try:
            if settings.GROUP:
                chat_member = await message.bot.get_chat_member(chat_id=settings.GROUP, user_id=target_user_id)
                user = chat_member.user
                user_info = {
                    "group_name": group_name,
                    "chat_id": chat_id,
                    "chat_username": chat_username,
                    "username": user.username or "",
                    "full_name": user.full_name,
                    "action": "ManualBan",
                    "user_id": str(target_user_id),
                }
            else:
                raise RuntimeError("未配置群组")
        except Exception:
            user_info = {
                "group_name": group_name,
                "chat_id": chat_id,
                "chat_username": chat_username,
                "username": "",
                "full_name": "Unknown",
                "action": "ManualBan",
                "user_id": str(target_user_id),
            }

    emby_results = await ban_emby_user(
        session=session,
        target_user_id=target_user_id,
        admin_id=message.from_user.id,
        reason="管理员手动封禁",
        bot=message.bot,
        user_info=user_info,
    )
    results.extend(emby_results)

    await session.commit()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="解除封禁", callback_data=f"unban:{target_user_id}"),
                InlineKeyboardButton(text="关闭", callback_data="close_message"),
            ]
        ]
    )

    await message.reply("\n".join(results), reply_markup=kb, parse_mode="MarkdownV2")
