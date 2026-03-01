from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import GroupConfigModel, MessageModel
from bot.utils.permissions import require_admin_command_access, require_admin_priv

router = Router(name="admin_stats")

COMMAND_META = {
    "name": "stats",
    "alias": "st",
    "usage": "/stats",
    "desc": "查看全局统计信息"
}


@router.message(Command("stats", "st"))
@require_admin_priv
@require_admin_command_access(COMMAND_META["name"])
async def admin_stats_command(message: Message, session: AsyncSession) -> None:
    try:
        group_query = select(func.count(GroupConfigModel.chat_id))
        group_result = await session.execute(group_query)
        total_groups = group_result.scalar() or 0
        enabled_query = select(func.count(GroupConfigModel.chat_id)).where(GroupConfigModel.is_message_save_enabled)
        enabled_result = await session.execute(enabled_query)
        enabled_groups = enabled_result.scalar() or 0
        message_query = select(func.count(MessageModel.id))
        message_result = await session.execute(message_query)
        total_messages = message_result.scalar() or 0
        recent_date = datetime.now(timezone.utc) - timedelta(days=30)
        recent_query = select(func.count(MessageModel.id)).where(MessageModel.created_at >= recent_date)
        recent_result = await session.execute(recent_query)
        recent_messages = recent_result.scalar() or 0
        stats_text = "📊 *全局统计信息*\n\n"
        stats_text += "*群组统计:*\n"
        stats_text += f"  总群组数: {total_groups}\n"
        stats_text += f"  启用群组: {enabled_groups}\n"
        stats_text += f"  禁用群组: {total_groups - enabled_groups}\n"
        stats_text += (
            f"  启用率: {(enabled_groups / total_groups * 100):.1f}%\n\n" if total_groups > 0 else "  启用率: 0%\n\n"
        )
        stats_text += "*消息统计:*\n"
        stats_text += f"  总消息数: {total_messages:,}\n"
        stats_text += f"  最近30天: {recent_messages:,}\n"
        stats_text += f"  日均消息: {recent_messages / 30:.1f}\n\n"
        stats_text += "*系统信息:*\n"
        stats_text += f"  统计时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
        stats_text += "  运行状态: 🟢 正常"
        await message.answer(stats_text, parse_mode="Markdown")
    except SQLAlchemyError as e:
        logger.error(f"❌ 查看全局统计失败: {e}")
        await message.answer("🔴 查看统计信息时发生错误")
