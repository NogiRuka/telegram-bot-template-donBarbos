"""
管理员命令处理器模块

本模块提供超级管理员对群组消息保存功能的管理命令，
包括全局启用/禁用、群组管理、数据清理等功能。

作者: Telegram Bot Template
创建时间: 2025-01-21
最后更新: 2025-01-21
"""

from datetime import datetime, timedelta
from functools import lru_cache

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.core.emby import EmbyClient
from bot.database.models import (
    EmbyUserModel,
    GroupConfigModel,
    GroupType,
    MessageModel,
    MessageSaveMode,
    UserExtendModel,
)
from bot.keyboards.inline.group_config import get_confirm_keyboard
from bot.services.message_export import MessageExportService

router = Router(name="admin_commands")


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


def is_super_admin(user_id: int) -> bool:
    """检查用户是否为超级管理员 (Owner)"""
    return user_id == settings.OWNER_ID


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

    # 2. 查找 Emby 关联
    stmt = select(UserExtendModel).where(UserExtendModel.user_id == target_user_id)
    result = await session.execute(stmt)
    user_extend = result.scalar_one_or_none()

    if user_extend and user_extend.emby_user_id:
        emby_user_id = user_extend.emby_user_id
        
        # 删除 Emby 账号
        if settings.EMBY_BASE_URL and settings.EMBY_API_KEY:
            try:
                emby_client = EmbyClient(settings.EMBY_BASE_URL, settings.EMBY_API_KEY)
                await emby_client.delete_user(emby_user_id)
                results.append(f"✅ Emby 账号已删除 (ID: {emby_user_id})")
            except Exception as e:
                logger.error(f"删除 Emby 账号失败: {e}")
                results.append(f"❌ Emby 账号删除失败: {e}")
        else:
            results.append("⚠️ 未配置 Emby API，跳过账号删除")

        # 软删除数据库 EmbyUserModel
        stmt_emby = select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id)
        result_emby = await session.execute(stmt_emby)
        emby_user = result_emby.scalar_one_or_none()

        if emby_user:
            emby_user.is_deleted = True
            # session.add(emby_user) # SQLAlchemy 自动追踪变更
            results.append("✅ Emby 用户数据已标记为删除")
        else:
            results.append("⚠️ 未找到本地 Emby 用户数据")
    else:
        results.append("ℹ️ 该用户未绑定 Emby 账号")

    await session.commit()
    await message.answer("\n".join(results))



@router.message(Command("admin_help"))
async def admin_help_command(message: Message) -> None:
    """
    管理员帮助命令

    Args:
        message: Telegram消息对象
    """
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return

    help_text = """
🛡️ *超级管理员命令帮助*

*群组管理:*
• `/admin_groups` - 查看所有群组配置
• `/admin_enable_group <chat_id>` - 启用群组消息保存
• `/admin_disable_group <chat_id>` - 禁用群组消息保存
• `/admin_group_info <chat_id>` - 查看群组详细信息

*数据管理:*
• `/admin_cleanup` - 清理过期数据
• `/admin_stats` - 查看全局统计
• `/admin_export_all` - 导出所有群组数据

*系统管理:*
• `/admin_broadcast <消息>` - 向所有群组广播消息
• `/admin_maintenance` - 进入维护模式
• `/admin_status` - 查看系统状态

*注意:* 所有管理员命令都需要超级管理员权限
    """

    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("admin_groups"))
async def admin_groups_command(message: Message, session: AsyncSession) -> None:
    """
    查看所有群组配置

    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return

    try:
        # 查询所有群组配置
        query = select(GroupConfigModel).order_by(GroupConfigModel.created_at.desc())
        result = await session.execute(query)
        configs = result.scalars().all()

        if not configs:
            await message.answer("📋 暂无群组配置")
            return

        # 构建群组列表
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

        # 如果内容太长，分页发送
        if len(groups_text) > 4000:
            # 简化显示
            groups_text = "📋 *所有群组配置*\n\n"
            enabled_count = sum(1 for c in configs if c.is_message_save_enabled)
            total_messages = sum(c.total_messages_saved for c in configs)

            groups_text += "📊 *统计信息:*\n"
            groups_text += f"  总群组数: {len(configs)}\n"
            groups_text += f"  启用群组: {enabled_count}\n"
            groups_text += f"  禁用群组: {len(configs) - enabled_count}\n"
            groups_text += f"  总消息数: {total_messages}\n\n"

            groups_text += "📝 *群组列表:*\n"
            for config in configs:
                status = "🟢" if config.is_message_save_enabled else "🔴"
                groups_text += f"  {status} 群组 {config.chat_id} ({config.total_messages_saved} 条消息)\n"

            if len(configs) > 20:
                groups_text += f"\n... 还有 {len(configs) - 20} 个群组"

        await message.answer(groups_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ 查看群组配置失败: {e}")
        await message.answer("🔴 查看群组配置时发生错误")


@router.message(Command("admin_enable_group"))
async def admin_enable_group_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    启用群组消息保存

    Args:
        message: Telegram消息对象
        command: 命令对象
        session: 数据库会话
    """
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return

    if not command.args:
        await message.answer("🔴 请提供群组ID\n用法: `/admin_enable_group <chat_id>`", parse_mode="Markdown")
        return

    try:
        chat_id = int(command.args)

        # 查找或创建群组配置
        config = await session.get(GroupConfigModel, chat_id)
        if not config:
            config = GroupConfigModel(
                chat_id=chat_id, group_type=GroupType.SUPERGROUP, is_enabled=True, save_mode=MessageSaveMode.ALL
            )
            session.add(config)
        else:
            config.is_message_save_enabled = True

        await session.commit()

        await message.answer(f"🟢 已启用群组 {chat_id} 的消息保存功能")

    except ValueError:
        await message.answer("🔴 无效的群组ID")
    except Exception as e:
        logger.error(f"❌ 启用群组失败: {e}")
        await message.answer("🔴 启用群组时发生错误")


@router.message(Command("admin_disable_group"))
async def admin_disable_group_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    禁用群组消息保存

    Args:
        message: Telegram消息对象
        command: 命令对象
        session: 数据库会话
    """
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return

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
    except Exception as e:
        logger.error(f"❌ 禁用群组失败: {e}")
        await message.answer("🔴 禁用群组时发生错误")


@router.message(Command("admin_group_info"))
async def admin_group_info_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    查看群组详细信息

    Args:
        message: Telegram消息对象
        command: 命令对象
        session: 数据库会话
    """
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return

    if not command.args:
        await message.answer("🔴 请提供群组ID\n用法: `/admin_group_info <chat_id>`", parse_mode="Markdown")
        return

    try:
        chat_id = int(command.args)

        # 获取群组配置
        config = await session.get(GroupConfigModel, chat_id)
        if not config:
            await message.answer(f"🔴 群组 {chat_id} 未找到配置")
            return

        # 获取消息统计
        export_service = MessageExportService(session)
        stats = await export_service.get_message_statistics(chat_id, days=30)

        # 构建信息文本
        info_text = f"📊 *群组 {chat_id} 详细信息*\n\n"

        # 基本配置
        status = "🟢 启用" if config.is_message_save_enabled else "🔴 禁用"
        group_type = "超级群组" if config.group_type == GroupType.SUPERGROUP else "普通群组"

        info_text += "*基本信息:*\n"
        info_text += f"  状态: {status}\n"
        info_text += f"  类型: {group_type}\n"
        info_text += f"  保存模式: {config.message_save_mode.value}\n"
        info_text += f"  创建时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        info_text += f"  更新时间: {config.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # 过滤设置
        info_text += "*过滤设置:*\n"
        info_text += f"  保存文本: {'🟢' if config.save_text else '🔴'}\n"
        info_text += f"  保存媒体: {'🟢' if config.save_media else '🔴'}\n"
        info_text += f"  保存转发: {'🟢' if config.save_forwarded else '🔴'}\n"
        info_text += f"  保存回复: {'🟢' if config.save_replies else '🔴'}\n"
        info_text += f"  保存机器人: {'🟢' if config.save_bot_messages else '🔴'}\n\n"

        # 统计信息
        if stats:
            info_text += "*统计信息（最近30天）:*\n"
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
    except Exception as e:
        logger.error(f"❌ 查看群组信息失败: {e}")
        await message.answer("🔴 查看群组信息时发生错误")


@router.message(Command("admin_cleanup"))
async def admin_cleanup_command(message: Message, session: AsyncSession) -> None:
    """
    清理过期数据

    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return

    try:
        # 清理90天前的消息
        cleanup_date = datetime.now() - timedelta(days=90)

        # 统计要删除的消息数
        count_query = select(func.count(MessageModel.id)).where(MessageModel.created_at < cleanup_date)
        result = await session.execute(count_query)
        message_count = result.scalar() or 0

        if message_count == 0:
            await message.answer("🟢 没有需要清理的过期数据")
            return

        # 确认清理
        await message.answer(
            f"🗑️ *数据清理确认*\n\n将删除 {message_count} 条90天前的消息\n此操作不可撤销，是否继续？",
            reply_markup=get_confirm_keyboard(f"admin_cleanup_confirm:{message_count}", "admin_cleanup_cancel"),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"❌ 数据清理失败: {e}")
        await message.answer("🔴 数据清理时发生错误")


@router.callback_query(F.data.startswith("admin_cleanup_confirm:"))
async def handle_cleanup_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    """
    处理清理确认

    Args:
        callback: 回调查询对象
        session: 数据库会话
    """
    if not is_super_admin(callback.from_user.id):
        await callback.answer("🔴 此操作仅限超级管理员", show_alert=True)
        return

    try:
        int(callback.data.split(":")[1])

        await callback.answer("🔄 正在清理数据...")

        # 执行清理
        cleanup_date = datetime.now() - timedelta(days=90)
        delete_query = delete(MessageModel).where(MessageModel.created_at < cleanup_date)

        result = await session.execute(delete_query)
        await session.commit()

        deleted_count = result.rowcount

        await callback.message.edit_text(
            f"🟢 *数据清理完成*\n\n"
            f"已删除 {deleted_count} 条过期消息\n"
            f"清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"❌ 确认清理失败: {e}")
        await callback.answer("🔴 清理失败", show_alert=True)


@router.callback_query(F.data == "admin_cleanup_cancel")
async def handle_cleanup_cancel(callback: CallbackQuery) -> None:
    """
    处理清理取消

    Args:
        callback: 回调查询对象
    """
    await callback.message.edit_text("🔴 已取消数据清理操作")
    await callback.answer("已取消")


@router.message(Command("admin_stats"))
async def admin_stats_command(message: Message, session: AsyncSession) -> None:
    """
    查看全局统计

    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return

    try:
        # 群组统计
        group_query = select(func.count(GroupConfigModel.chat_id))
        group_result = await session.execute(group_query)
        total_groups = group_result.scalar() or 0

        enabled_query = select(func.count(GroupConfigModel.chat_id)).where(GroupConfigModel.is_message_save_enabled)
        enabled_result = await session.execute(enabled_query)
        enabled_groups = enabled_result.scalar() or 0

        # 消息统计
        message_query = select(func.count(MessageModel.id))
        message_result = await session.execute(message_query)
        total_messages = message_result.scalar() or 0

        # 最近30天消息
        recent_date = datetime.now() - timedelta(days=30)
        recent_query = select(func.count(MessageModel.id)).where(MessageModel.created_at >= recent_date)
        recent_result = await session.execute(recent_query)
        recent_messages = recent_result.scalar() or 0

        # 构建统计信息
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
        stats_text += f"  统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        stats_text += "  运行状态: 🟢 正常"

        await message.answer(stats_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"❌ 查看全局统计失败: {e}")
        await message.answer("🔴 查看统计信息时发生错误")


# 导出路由
__all__ = ["router"]
