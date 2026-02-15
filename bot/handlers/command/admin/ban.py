"""
封禁用户命令模块
"""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.services.admin_service import ban_emby_user
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import require_admin_priv, require_admin_command_access
from bot.utils.text import escape_markdown_v2

router = Router(name="command_ban")

COMMAND_META = {
    "name": "ban",
    "alias": None,
    "usage": "/ban <user_id>",
    "desc": "封禁用户"
}


@router.message(Command("ban"))
@private_chat_only
@require_admin_priv
@require_admin_command_access(COMMAND_META["name"])
async def ban_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    封禁用户命令

    功能:
    1. 从群组移除用户
    2. 删除 Emby 账号 (如果存在)
    3. 软删除数据库中的 Emby 用户数据

    用法: /ban <telegram_user_id>
    """
    if not command.args:
        await message.reply("⚠️ 请提供 Telegram 用户 ID\n用法: `/ban <user_id>`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(command.args)
    except ValueError:
        await message.reply("❌ 无效的用户 ID，必须为数字")
        return

    results = []

    # 1. 从群组移除
    if settings.GROUP:
        try:
            await message.bot.ban_chat_member(chat_id=settings.GROUP, user_id=target_user_id)
            results.append("✅ 已从群组移除并封禁")
        except Exception as e:
            logger.warning(f"无法从群组移除用户 {target_user_id}: {e}")
            safe_e = escape_markdown_v2(str(e))
            results.append(f"⚠️ 无法从群组移除: {safe_e}")
    else:
        results.append("ℹ️ 未配置群组，跳过群组移除")

    # 2. 调用封禁服务
    group_name = "Private"
    chat_id = None
    chat_username = None

    if message.chat.type != "private":
        group_name = message.chat.title
        chat_id = message.chat.id
        chat_username = message.chat.username
    elif settings.GROUP:
        group_name = f"Group{settings.GROUP}"
        try:
            chat_id = int(settings.GROUP)
        except (ValueError, TypeError):
            chat_username = settings.GROUP

    from sqlalchemy import select

    from bot.database.models import UserModel

    db_user_result = await session.execute(select(UserModel).where(UserModel.id == target_user_id))
    db_user = db_user_result.scalar_one_or_none()

    if db_user:
        user_info = {
            "group_name": group_name,
            "chat_id": chat_id,
            "chat_username": chat_username,
            "username": f"@{db_user.username}" if db_user.username else "Unknown",
            "full_name": db_user.get_full_name(),
            "action": "ManualBan"
        }
    else:
        try:
            if settings.GROUP:
                chat_member = await message.bot.get_chat_member(chat_id=settings.GROUP, user_id=target_user_id)
                user = chat_member.user
                full_name = user.full_name
                username = f"@{user.username}" if user.username else "Unknown"
                user_info = {
                    "group_name": group_name,
                    "chat_id": chat_id,
                    "chat_username": chat_username,
                    "username": username,
                    "full_name": full_name,
                    "action": "ManualBan"
                }
            else:
                msg = "No group configured"
                raise Exception(msg)
        except Exception:
            user_info = {
                "group_name": group_name,
                "chat_id": chat_id,
                "chat_username": chat_username,
                "username": "Unknown",
                "full_name": "Unknown",
                "action": "ManualBan"
            }

    emby_results = await ban_emby_user(
        session=session,
        target_user_id=target_user_id,
        admin_id=message.from_user.id,
        reason="管理员手动封禁",
        bot=message.bot,
        user_info=user_info
    )
    results.extend(emby_results)

    await session.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔓 解除封禁", callback_data=f"unban:{target_user_id}"),
            InlineKeyboardButton(text="❌ 关闭", callback_data="close_message")
        ]
    ])

    await message.reply("\n".join(results), reply_markup=kb, parse_mode="MarkdownV2")
