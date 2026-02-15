from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import GroupConfigModel, GroupType, MessageSaveMode
from bot.services.message_export import MessageExportService
from bot.utils.permissions import require_admin_feature, require_admin_priv

router = Router(name="admin_group")

MAX_MESSAGE_LENGTH = 4000
SUMMARY_LIMIT = 20


@router.message(Command("groups"))
@require_admin_priv
async def admin_groups_command(message: Message, session: AsyncSession) -> None:
    """
    查看所有群组配置
    """
    try:
        query = select(GroupConfigModel).order_by(GroupConfigModel.created_at.desc())
        result = await session.execute(query)
        configs = result.scalars().all()
        if not configs:
            await message.answer("📋 暂无群组配置")
            return
        groups_text = "📋 *所有群组配置*\n\n"
        for config in configs:
            status = "🟢 启用" if config.is_message_save_enabled else "🔴 禁用"
            group_type = "超级群组" if config.group_type == GroupType.SUPERGROUP else "普通群组"
            groups_text += f"*群组 {config.chat_id}*\n"
            groups_text += f"  状态: {status}\n"
            groups_text += f"  类型: {group_type}\n"
            groups_text += f"  保存模式: {config.message_save_mode.value}\n"
            groups_text += f"  已保存消息: {config.total_messages_saved}\n"
            groups_text += f"  创建时间: {config.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        if len(groups_text) > MAX_MESSAGE_LENGTH:
            groups_text = "📋 *所有群组配置*\n\n"
            enabled_count = sum(1 for c in configs if c.is_message_save_enabled)
            total_messages = sum(c.total_messages_saved for c in configs)
            groups_text += "📊 *统计信息:*\n"
            groups_text += f"  总群组数: {len(configs)}\n"
            groups_text += f"  启用群组: {enabled_count}\n"
            groups_text += f"  禁用群组: {len(configs) - enabled_count}\n"
            groups_text += f"  总消息数: {total_messages}\n\n"
            groups_text += "📝 *群组列表:*\n"
            for config in configs[:SUMMARY_LIMIT]:
                status = "🟢" if config.is_message_save_enabled else "🔴"
                groups_text += f"  {status} 群组 {config.chat_id} ({config.total_messages_saved} 条消息)\n"
            if len(configs) > SUMMARY_LIMIT:
                groups_text += f"\n... 还有 {len(configs) - SUMMARY_LIMIT} 个群组"
        await message.answer(groups_text, parse_mode="Markdown")
    except SQLAlchemyError as e:
        logger.error(f"❌ 查看群组配置失败: {e}")
        await message.answer("🔴 查看群组配置时发生错误")


@router.message(Command("enable_group"))
@require_admin_priv
async def admin_enable_group_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    启用群组消息保存
    """
    if not command.args:
        await message.answer("🔴 请提供群组ID\n用法: `/admin_enable_group <chat_id>`", parse_mode="Markdown")
        return
    try:
        chat_id = int(command.args)
        config = await session.get(GroupConfigModel, chat_id)
        if not config:
            config = GroupConfigModel(
                chat_id=chat_id,
                group_type=GroupType.SUPERGROUP,
                is_enabled=True,
                save_mode=MessageSaveMode.ALL,
            )
            session.add(config)
        else:
            config.is_message_save_enabled = True
        await session.commit()
        await message.answer(f"🟢 已启用群组 {chat_id} 的消息保存功能")
    except ValueError:
        await message.answer("🔴 无效的群组ID")
    except SQLAlchemyError as e:
        logger.error(f"❌ 启用群组失败: {e}")
        await message.answer("🔴 启用群组时发生错误")


@router.message(Command("disable_group"))
@require_admin_priv
async def admin_disable_group_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    禁用群组消息保存
    """
    if not command.args:
        await message.answer("🔴 请提供群组ID\n用法: `/admin_disable_group <chat_id>`", parse_mode="Markdown")
        return
    try:
        chat_id = int(command.args)
        config = await session.get(GroupConfigModel, chat_id)
        if not config:
            await message.answer(f"🔴 群组 {chat_id} 未找到配置")
            return
        config.is_message_save_enabled = False
        await session.commit()
        await message.answer(f"🔴 已禁用群组 {chat_id} 的消息保存功能")
    except ValueError:
        await message.answer("🔴 无效的群组ID")
    except SQLAlchemyError as e:
        logger.error(f"❌ 禁用群组失败: {e}")
        await message.answer("🔴 禁用群组时发生错误")


@router.message(Command("group_info"))
@require_admin_priv

async def admin_group_info_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    查看群组详细信息
    """
    if not command.args:
        await message.answer("🔴 请提供群组ID\n用法: `/admin_group_info <chat_id>`", parse_mode="Markdown")
        return
    try:
        chat_id = int(command.args)
        config = await session.get(GroupConfigModel, chat_id)
        if not config:
            await message.answer(f"🔴 群组 {chat_id} 未找到配置")
            return
        export_service = MessageExportService(session)
        stats = await export_service.get_message_statistics(chat_id, days=30)
        info_text = f"📊 *群组 {chat_id} 详细信息*\n\n"
        status = "🟢 启用" if config.is_message_save_enabled else "🔴 禁用"
        group_type = "超级群组" if config.group_type == GroupType.SUPERGROUP else "普通群组"
        info_text += "*基本信息:*\n"
        info_text += f"  状态: {status}\n"
        info_text += f"  类型: {group_type}\n"
        info_text += f"  保存模式: {config.message_save_mode.value}\n"
        info_text += f"  创建时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        info_text += f"  更新时间: {config.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        info_text += "*过滤设置:*\n"
        info_text += f"  保存文本: {'🟢' if config.save_text else '🔴'}\n"
        info_text += f"  保存媒体: {'🟢' if config.save_media else '🔴'}\n"
        info_text += f"  保存转发: {'🟢' if config.save_forwarded else '🔴'}\n"
        info_text += f"  保存回复: {'🟢' if config.save_replies else '🔴'}\n"
        info_text += f"  保存机器人: {'🟢' if config.save_bot_messages else '🔴'}\n\n"
        if stats:
            info_text += "*统计信息(最近30天):*\n"
            info_text += f"  总消息数: {stats.get('total_messages', 0)}\n"
            info_text += f"  活跃用户: {len(stats.get('top_users', []))}\n"
            if stats.get("message_types"):
                info_text += f"  消息类型: {len(stats['message_types'])} 种\n"
        info_text += "\n*历史统计:*\n"
        info_text += f"  累计消息: {config.total_messages_saved}\n"
        info_text += f"  累计用户: {config.total_users}\n"
        await message.answer(info_text, parse_mode="Markdown")
    except ValueError:
        await message.answer("🔴 无效的群组ID")
    except SQLAlchemyError as e:
        logger.error(f"❌ 查看群组信息失败: {e}")
        await message.answer("🔴 查看群组信息时发生错误")
