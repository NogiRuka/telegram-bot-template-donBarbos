"""
封禁用户命令模块
"""
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.services.admin_service import ban_emby_user

router = Router(name="command_ban")


def is_admin(user_id: int) -> bool:
    """检查用户是否为管理员 (Owner 或 Admin)"""
    if user_id == settings.OWNER_ID:
        return True
    if settings.ADMIN_IDS:
        try:
            admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip() and x.strip().isdigit()]
            return user_id in admin_ids
        except Exception:
            return False
    return False


@router.message(Command("ban"))
async def ban_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    封禁用户命令

    功能:
    1. 从群组移除用户
    2. 删除 Emby 账号 (如果存在)
    3. 软删除数据库中的 Emby 用户数据

    用法: /ban <telegram_user_id>
    """
    if not is_admin(message.from_user.id):
        return

    if not command.args:
        await message.answer("⚠️ 请提供 Telegram 用户 ID\n用法: `/ban <user_id>`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(command.args)
    except ValueError:
        await message.answer("❌ 无效的用户 ID，必须为数字")
        return

    results = []

    # 1. 从群组移除
    if settings.GROUP:
        try:
            # 尝试踢出成员 (ban_chat_member 会踢出并拉黑)
            await message.bot.ban_chat_member(chat_id=settings.GROUP, user_id=target_user_id)
            results.append("✅ 已从群组移除并封禁")
        except Exception as e:
            logger.warning(f"无法从群组移除用户 {target_user_id}: {e}")
            results.append(f"⚠️ 无法从群组移除: {e}")
    else:
        results.append("ℹ️ 未配置群组，跳过群组移除")

    # 2. 调用封禁服务 (Emby 账号删除 + 软删除 + 审计日志)
    emby_results = await ban_emby_user(
        session=session,
        target_user_id=target_user_id,
        admin_id=message.from_user.id,
        reason="管理员手动封禁"
    )
    results.extend(emby_results)

    await session.commit()
    await message.answer("\n".join(results))
