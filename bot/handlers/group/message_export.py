"""
消息导出处理器模块（子包）
"""
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import GroupConfigModel
from bot.keyboards.inline.group_config import (
    get_message_export_keyboard,
)
from bot.services.message_export import MessageExportService

router = Router(name="message_export")


class MessageExportStates(StatesGroup):
    waiting_for_search_text = State()
    waiting_for_date_range = State()
    waiting_for_user_id = State()


@router.message(Command("export_messages"))
async def export_messages_command(message: Message, session: AsyncSession) -> None:
    try:
        if message.chat.type not in ["group", "supergroup"]:
            await message.answer("❌ 此命令只能在群组中使用")
            return
        chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            await message.answer("❌ 只有群组管理员可以使用此命令")
            return
        config = await session.get(GroupConfigModel, message.chat.id)
        if not config or not config.is_message_save_enabled:
            await message.answer(
                "❌ 此群组未启用消息保存功能\n" "请先使用 /group_config 命令启用消息保存"
            )
            return
        await message.answer(
            "📤 **消息导出功能**\n\n" "请选择导出格式和时间范围：",
            reply_markup=get_message_export_keyboard(message.chat.id),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"导出消息命令处理失败: {e}")
        await message.answer("❌ 处理命令时发生错误，请稍后重试")


@router.message(Command("message_stats"))
async def message_stats_command(message: Message, session: AsyncSession) -> None:
    try:
        if message.chat.type not in ["group", "supergroup"]:
            await message.answer("❌ 此命令只能在群组中使用")
            return
        config = await session.get(GroupConfigModel, message.chat.id)
        if not config or not config.is_message_save_enabled:
            await message.answer(
                "❌ 此群组未启用消息保存功能\n" "请先使用 /group_config 命令启用消息保存"
            )
            return
        export_service = MessageExportService(session)
        stats = await export_service.get_message_statistics(message.chat.id, days=30)
        if not stats:
            await message.answer("❌ 获取统计信息失败")
            return
        stats_text = "📊 **群组消息统计（最近30天）**\n\n"
        stats_text += f"📈 **总消息数**: {stats['total_messages']}\n\n"
        if stats["message_types"]:
            stats_text += "📝 **消息类型分布**:\n"
            type_names = {
                "text": "文本消息",
                "photo": "图片消息",
                "video": "视频消息",
                "audio": "音频消息",
                "voice": "语音消息",
                "document": "文档消息",
                "sticker": "贴纸消息",
                "animation": "动图消息",
                "location": "位置消息",
                "contact": "联系人消息",
                "poll": "投票消息",
                "other": "其他消息",
            }
            for msg_type, count in stats["message_types"].items():
                type_name = type_names.get(msg_type, msg_type)
                stats_text += f"  • {type_name}: {count}\n"
            stats_text += "\n"
        if stats["top_users"]:
            stats_text += "👥 **最活跃用户（前5名）**:\n"
            for i, user in enumerate(stats["top_users"][:5], 1):
                stats_text += f"  {i}. 用户 {user['user_id']}: {user['message_count']} 条消息\n"
            stats_text += "\n"
        if stats["daily_statistics"]:
            recent_days = stats["daily_statistics"][-7:]
            if recent_days:
                avg_daily = sum(day["count"] for day in recent_days) / len(recent_days)
                stats_text += f"📅 **最近7天平均**: {avg_daily:.1f} 条消息/天\n"
        stats_text += f"\n🕐 统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        await message.answer(stats_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"消息统计命令处理失败: {e}")
        await message.answer("❌ 获取统计信息时发生错误，请稍后重试")


@router.callback_query(F.data.startswith("export:"))
async def handle_export_format(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        data_parts = callback.data.split(":")
        export_format = data_parts[1]
        chat_id = int(data_parts[2])
        chat_member = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            await callback.answer("❌ 只有群组管理员可以导出消息", show_alert=True)
            return
        await callback.answer("🔄 正在准备导出...")
        export_service = MessageExportService(session)
        start_date = datetime.now() - timedelta(days=30)
        if export_format == "txt":
            file_content = await export_service.export_to_txt(chat_id, start_date=start_date, limit=5000)
            filename = f"messages_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        elif export_format == "csv":
            file_content = await export_service.export_to_csv(chat_id, start_date=start_date, limit=5000)
            filename = f"messages_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_format == "json":
            file_content = await export_service.export_to_json(chat_id, start_date=start_date, limit=5000)
            filename = f"messages_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            await callback.message.edit_text("❌ 不支持的导出格式")
            return
        document = BufferedInputFile(file_content.read(), filename=filename)
        await callback.message.answer_document(
            document=document,
            caption=(
                f"📤 群组消息导出完成\n"
                f"格式: {export_format.upper()}\n"
                f"时间范围: 最近30天\n"
                f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
        )
        await callback.message.delete()
    except Exception as e:
        logger.error(f"处理导出格式失败: {e}")
        await callback.answer("❌ 导出失败，请稍后重试", show_alert=True)


@router.callback_query(F.data.startswith("export_range:"))
async def handle_export_range(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        data_parts = callback.data.split(":")
        range_type = data_parts[1]
        chat_id = int(data_parts[2])
        chat_member = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            await callback.answer("❌ 只有群组管理员可以导出消息", show_alert=True)
            return
        range_text = ""
        if range_type == "7d":
            datetime.now() - timedelta(days=7)
            range_text = "最近7天"
        elif range_type == "30d":
            datetime.now() - timedelta(days=30)
            range_text = "最近30天"
        elif range_type == "all":
            range_text = "全部消息"
        await callback.message.edit_text(
            f"📤 **消息导出功能**\n\n" f"已选择时间范围: **{range_text}**\n" f"请选择导出格式：",
            reply_markup=get_message_export_keyboard(chat_id),
            parse_mode="Markdown",
        )
        await callback.answer(f"✅ 已选择时间范围: {range_text}")
    except Exception as e:
        logger.error(f"处理导出时间范围失败: {e}")
        await callback.answer("❌ 处理失败，请稍后重试", show_alert=True)


@router.message(Command("search_messages"))
async def search_messages_command(message: Message, state: FSMContext) -> None:
    try:
        if message.chat.type not in ["group", "supergroup"]:
            await message.answer("❌ 此命令只能在群组中使用")
            return
        chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            await message.answer("❌ 只有群组管理员可以搜索消息")
            return
        await message.answer("🔍 **消息搜索功能**\n\n" "请输入要搜索的关键词：", parse_mode="Markdown")
        await state.set_state(MessageExportStates.waiting_for_search_text)
        await state.update_data(chat_id=message.chat.id)
    except Exception as e:
        logger.error(f"搜索消息命令处理失败: {e}")
        await message.answer("❌ 处理命令时发生错误，请稍后重试")


@router.message(StateFilter(MessageExportStates.waiting_for_search_text))
async def handle_search_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        search_text = message.text.strip()
        if not search_text:
            await message.answer("❌ 请输入有效的搜索关键词")
            return
        data = await state.get_data()
        chat_id = data.get("chat_id")
        if not chat_id:
            await message.answer("❌ 会话状态错误，请重新开始")
            await state.clear()
            return
        await message.answer("🔍 正在搜索消息...")
        export_service = MessageExportService(session)
        messages, total_count = await export_service.get_messages(
            chat_id=chat_id,
            search_text=search_text,
            limit=20,
            start_date=datetime.now() - timedelta(days=30),
        )
        if not messages:
            await message.answer(f'🔍 未找到包含 "{search_text}" 的消息')
            await state.clear()
            return
        result_text = "🔍 **搜索结果**\n\n"
        result_text += f"关键词: `{search_text}`\n"
        result_text += f"找到 {total_count} 条相关消息（显示前20条）\n\n"
        for i, msg in enumerate(messages[:10], 1):
            result_text += f"**{i}.** 用户 {msg.user_id} ({msg.created_at.strftime('%m-%d %H:%M')})\n"
            content = msg.text or msg.caption or "[媒体消息]"
            if len(content) > 100:
                content = content[:100] + "..."
            result_text += f"   {content}\n\n"
        if len(messages) > 10:
            result_text += f"... 还有 {len(messages) - 10} 条消息\n\n"
        result_text += "💡 使用 /export_messages 命令可以导出完整的搜索结果"
        await message.answer(result_text, parse_mode="Markdown")
        await state.clear()
    except Exception as e:
        logger.error(f"处理搜索文本失败: {e}")
        await message.answer("❌ 搜索失败，请稍后重试")
        await state.clear()


__all__ = ["router"]
