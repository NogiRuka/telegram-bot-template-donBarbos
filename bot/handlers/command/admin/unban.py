"""
解除封禁命令模块
"""
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.services.admin_service import unban_user_service
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import require_admin_command_access, require_admin_priv

router = Router(name="command_unban")

COMMAND_META = {
    "name": "unban",
    "alias": "ub",
    "usage": "/unban <user_id>",
    "desc": "解除封禁"
}


@router.message(Command("unban", "ub"))
@private_chat_only
@require_admin_priv
@require_admin_command_access(COMMAND_META["name"])
async def unban_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    解除封禁命令
    用法: /unban <user_id>
    """
    if not command.args:
        await message.reply("⚠️ 请提供 Telegram 用户 ID\n用法: `/unban <user_id>`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(command.args)
    except ValueError:
        await message.reply("❌ 无效的用户 ID，必须为数字")
        return

    await process_unban(message, target_user_id, session, message.from_user.id)


@router.callback_query(F.data.startswith("unban:"))
@require_admin_priv
async def unban_callback(query: CallbackQuery, session: AsyncSession) -> None:
    """处理解除封禁按钮点击"""
    target_user_id = int(query.data.split(":")[1])

    await query.message.edit_reply_markup(reply_markup=None)

    await process_unban(query.message, target_user_id, session, query.from_user.id, is_callback=True)
    await query.answer("已解除封禁")


@router.callback_query(F.data == "close_message")
@require_admin_priv
async def close_callback(query: CallbackQuery, session: AsyncSession) -> None:
    """关闭消息"""
    await query.message.delete()


async def process_unban(
    message: Message,
    target_user_id: int,
    session: AsyncSession,
    admin_id: int,
    is_callback: bool = False
) -> None:
    """处理解封核心逻辑"""
    results = []

    # 1. Telegram 解封
    if settings.GROUP:
        try:
            await message.bot.unban_chat_member(chat_id=settings.GROUP, user_id=target_user_id, only_if_banned=True)
            results.append("✅ 已解除群组封禁")
        except Exception as e:
            logger.warning(f"无法解封用户 {target_user_id}: {e}")
            results.append(f"⚠️ 群组解封失败: {e}")
    else:
        results.append("ℹ️ 未配置群组，跳过群组解封")

    # 2. 记录审计日志并通知
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

    user_info = {
        "group_name": group_name,
        "chat_id": chat_id,
        "chat_username": chat_username,
        "username": "",
        "full_name": "Unknown",
        "action": "ManualUnban",
        "user_id": str(target_user_id),
    }

    service_results = await unban_user_service(
        session=session,
        target_user_id=target_user_id,
        admin_id=admin_id,
        reason="管理员手动解封",
        bot=message.bot,
        user_info=user_info
    )
    results.extend(service_results)

    await session.commit()

    text = "\n".join(results)
    await message.reply(text)
