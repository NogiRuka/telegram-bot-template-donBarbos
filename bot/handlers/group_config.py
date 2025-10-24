"""
群组配置管理处理器模块

本模块实现了群组消息保存配置的管理功能，
包括启用/禁用消息保存、设置保存模式等。

作者: Telegram Bot Template
创建时间: 2025-01-21
最后更新: 2025-01-21
"""

import json
import logging
from typing import List, Optional

from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# 移除db_session导入，使用依赖注入
from bot.database.models import (
    GroupConfigModel, GroupType, MessageSaveMode,
    MessageModel, UserModel
)
from bot.filters.admin import AdminFilter
from bot.keyboards.inline.group_config import (
    get_group_config_keyboard,
    get_save_mode_keyboard,
    get_confirm_keyboard
)

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = Router()


class GroupConfigStates(StatesGroup):
    """群组配置状态组"""
    waiting_for_keywords = State()
    waiting_for_time_range = State()
    waiting_for_limits = State()


@router.message(Command("group_config"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]), AdminFilter())
async def cmd_group_config(message: types.Message, session: AsyncSession) -> None:
    """
    群组配置命令
    
    显示当前群组的消息保存配置。
    
    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    try:
        # 获取群组配置
        result = await session.execute(
            select(GroupConfigModel).where(
                GroupConfigModel.chat_id == message.chat.id,
                GroupConfigModel.is_deleted == False
            )
        )
        config = result.scalar_one_or_none()
        
        if not config:
            # 创建默认配置
            group_type = GroupType.SUPERGROUP if message.chat.type == "supergroup" else GroupType.GROUP
            config = GroupConfigModel.create_for_group(
                chat_id=message.chat.id,
                chat_title=message.chat.title,
                chat_username=message.chat.username,
                group_type=group_type,
                configured_by_user_id=message.from_user.id
            )
            session.add(config)
            await session.commit()
        
        # 获取消息统计
        stats_result = await session.execute(
            select(func.count(MessageModel.id)).where(
                MessageModel.chat_id == message.chat.id,
                MessageModel.is_deleted == False
            )
        )
        total_messages = stats_result.scalar() or 0
        
        # 构建配置信息文本
        config_text = f"""
🔧 **群组消息保存配置**

📊 **基本信息**
• 群组: {config.get_group_info_display()}
• 群组ID: `{config.chat_id}`
• 群组类型: {config.group_type.value}

⚙️ **保存设置**
• 状态: {config.get_save_status_display()}
• 保存模式: {config.message_save_mode.value}
• 已保存消息: {config.total_messages_saved} 条
• 数据库总消息: {total_messages} 条

📋 **过滤设置**
• 文本消息: {'✅' if config.save_text_messages else '❌'}
• 媒体消息: {'✅' if config.save_media_messages else '❌'}
• 转发消息: {'✅' if config.save_forwarded_messages else '❌'}
• 回复消息: {'✅' if config.save_reply_messages else '❌'}
• 机器人消息: {'✅' if config.save_bot_messages else '❌'}

⏰ **时间设置**
• 开始时间: {config.save_start_date.strftime('%Y-%m-%d %H:%M') if config.save_start_date else '未设置'}
• 结束时间: {config.save_end_date.strftime('%Y-%m-%d %H:%M') if config.save_end_date else '未设置'}

📏 **限制设置**
• 每日最大消息数: {config.max_messages_per_day or '无限制'}
• 最大文件大小: {config.max_file_size_mb or '无限制'} MB

🔍 **关键词过滤**
• 包含关键词: {len(json.loads(config.include_keywords)) if config.include_keywords else 0} 个
• 排除关键词: {len(json.loads(config.exclude_keywords)) if config.exclude_keywords else 0} 个

📝 **备注**: {config.notes or '无'}
        """
        
        await message.reply(
            config_text,
            reply_markup=get_group_config_keyboard(config.id),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"显示群组配置失败: {e}")
        await message.reply("❌ 获取群组配置失败，请稍后重试。")


@router.callback_query(F.data.startswith("group_config:"))
async def handle_group_config_callback(callback: types.CallbackQuery, session: AsyncSession) -> None:
    """
    处理群组配置回调
    
    Args:
        callback: 回调查询对象
        session: 数据库会话
    """
    try:
        action_data = callback.data.split(":")
        action = action_data[1]
        config_id = int(action_data[2])
        
        # 获取配置
        result = await session.execute(
            select(GroupConfigModel).where(GroupConfigModel.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            await callback.answer("❌ 配置不存在")
            return
        
        if action == "toggle_enable":
            # 切换启用状态
            config.is_message_save_enabled = not config.is_message_save_enabled
            if config.is_message_save_enabled and config.message_save_mode == MessageSaveMode.DISABLED:
                config.message_save_mode = MessageSaveMode.ALL
            elif not config.is_message_save_enabled:
                config.message_save_mode = MessageSaveMode.DISABLED
            
            await session.commit()
            
            status = "启用" if config.is_message_save_enabled else "禁用"
            await callback.answer(f"✅ 已{status}消息保存")
            
            # 更新键盘
            await callback.message.edit_reply_markup(
                reply_markup=get_group_config_keyboard(config.id)
            )
        
        elif action == "change_mode":
            # 显示保存模式选择
            await callback.message.edit_text(
                "🔧 **选择消息保存模式**\n\n"
                "• **保存所有消息**: 保存群组中的所有消息\n"
                "• **仅保存文本**: 只保存文本消息\n"
                "• **仅保存媒体**: 只保存图片、视频等媒体消息\n"
                "• **仅保存重要消息**: 只保存回复和转发消息\n"
                "• **禁用**: 停止保存消息",
                reply_markup=get_save_mode_keyboard(config.id),
                parse_mode="Markdown"
            )
        
        elif action == "toggle_text":
            config.save_text_messages = not config.save_text_messages
            await session.commit()
            await callback.answer(f"✅ 文本消息保存已{'启用' if config.save_text_messages else '禁用'}")
            await callback.message.edit_reply_markup(
                reply_markup=get_group_config_keyboard(config.id)
            )
        
        elif action == "toggle_media":
            config.save_media_messages = not config.save_media_messages
            await session.commit()
            await callback.answer(f"✅ 媒体消息保存已{'启用' if config.save_media_messages else '禁用'}")
            await callback.message.edit_reply_markup(
                reply_markup=get_group_config_keyboard(config.id)
            )
        
        elif action == "toggle_forwarded":
            config.save_forwarded_messages = not config.save_forwarded_messages
            await session.commit()
            await callback.answer(f"✅ 转发消息保存已{'启用' if config.save_forwarded_messages else '禁用'}")
            await callback.message.edit_reply_markup(
                reply_markup=get_group_config_keyboard(config.id)
            )
        
        elif action == "toggle_reply":
            config.save_reply_messages = not config.save_reply_messages
            await session.commit()
            await callback.answer(f"✅ 回复消息保存已{'启用' if config.save_reply_messages else '禁用'}")
            await callback.message.edit_reply_markup(
                reply_markup=get_group_config_keyboard(config.id)
            )
        
        elif action == "toggle_bot":
            config.save_bot_messages = not config.save_bot_messages
            await session.commit()
            await callback.answer(f"✅ 机器人消息保存已{'启用' if config.save_bot_messages else '禁用'}")
            await callback.message.edit_reply_markup(
                reply_markup=get_group_config_keyboard(config.id)
            )
        
        elif action == "clear_messages":
            # 显示确认对话框
            await callback.message.edit_text(
                "⚠️ **确认清空消息**\n\n"
                f"您确定要清空群组 `{config.chat_title}` 的所有已保存消息吗？\n\n"
                "**此操作不可撤销！**",
                reply_markup=get_confirm_keyboard(f"confirm_clear:{config.id}", f"group_config_back:{config.id}"),
                parse_mode="Markdown"
            )
        
        elif action == "refresh":
            # 刷新配置显示
            await cmd_group_config(callback.message, session)
            await callback.answer("🔄 配置已刷新")
        
    except Exception as e:
        logger.error(f"处理群组配置回调失败: {e}")
        await callback.answer("❌ 操作失败，请稍后重试")


@router.callback_query(F.data.startswith("save_mode:"))
async def handle_save_mode_callback(callback: types.CallbackQuery, session: AsyncSession) -> None:
    """
    处理保存模式回调
    
    Args:
        callback: 回调查询对象
        session: 数据库会话
    """
    try:
        action_data = callback.data.split(":")
        mode = action_data[1]
        config_id = int(action_data[2])
        
        # 获取配置
        result = await session.execute(
            select(GroupConfigModel).where(GroupConfigModel.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            await callback.answer("❌ 配置不存在")
            return
        
        # 更新保存模式
        if mode == "all":
            config.message_save_mode = MessageSaveMode.ALL
            config.is_message_save_enabled = True
        elif mode == "text_only":
            config.message_save_mode = MessageSaveMode.TEXT_ONLY
            config.is_message_save_enabled = True
        elif mode == "media_only":
            config.message_save_mode = MessageSaveMode.MEDIA_ONLY
            config.is_message_save_enabled = True
        elif mode == "important_only":
            config.message_save_mode = MessageSaveMode.IMPORTANT_ONLY
            config.is_message_save_enabled = True
        elif mode == "disabled":
            config.message_save_mode = MessageSaveMode.DISABLED
            config.is_message_save_enabled = False
        
        await session.commit()
        
        mode_names = {
            "all": "保存所有消息",
            "text_only": "仅保存文本",
            "media_only": "仅保存媒体",
            "important_only": "仅保存重要消息",
            "disabled": "已禁用"
        }
        
        await callback.answer(f"✅ 保存模式已设置为: {mode_names[mode]}")
        
        # 返回配置页面
        await cmd_group_config(callback.message, session)
        
    except Exception as e:
        logger.error(f"处理保存模式回调失败: {e}")
        await callback.answer("❌ 操作失败，请稍后重试")


@router.callback_query(F.data.startswith("confirm_clear:"))
async def handle_confirm_clear_callback(callback: types.CallbackQuery, session: AsyncSession) -> None:
    """
    处理确认清空消息回调
    
    Args:
        callback: 回调查询对象
        session: 数据库会话
    """
    try:
        config_id = int(callback.data.split(":")[1])
        
        # 获取配置
        result = await session.execute(
            select(GroupConfigModel).where(GroupConfigModel.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            await callback.answer("❌ 配置不存在")
            return
        
        # 软删除该群组的所有消息
        messages_result = await session.execute(
            select(MessageModel).where(
                MessageModel.chat_id == config.chat_id,
                MessageModel.is_deleted == False
            )
        )
        messages = messages_result.scalars().all()
        
        deleted_count = 0
        for message in messages:
            message.soft_delete()
            deleted_count += 1
        
        # 重置配置统计
        config.total_messages_saved = 0
        config.last_message_date = None
        
        await session.commit()
        
        await callback.answer(f"✅ 已清空 {deleted_count} 条消息")
        
        # 返回配置页面
        await cmd_group_config(callback.message, session)
        
    except Exception as e:
        logger.error(f"清空消息失败: {e}")
        await callback.answer("❌ 清空失败，请稍后重试")


@router.callback_query(F.data.startswith("group_config_back:"))
async def handle_group_config_back_callback(callback: types.CallbackQuery, session: AsyncSession) -> None:
    """
    处理返回群组配置回调
    
    Args:
        callback: 回调查询对象
        session: 数据库会话
    """
    try:
        # 返回配置页面
        await cmd_group_config(callback.message, session)
        
    except Exception as e:
        logger.error(f"返回群组配置失败: {e}")
        await callback.answer("❌ 操作失败，请稍后重试")


@router.message(Command("save_enable"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]), AdminFilter())
async def cmd_save_enable(message: types.Message, session: AsyncSession) -> None:
    """
    快速启用消息保存命令
    
    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    try:
        # 获取或创建群组配置
        result = await session.execute(
            select(GroupConfigModel).where(
                GroupConfigModel.chat_id == message.chat.id,
                GroupConfigModel.is_deleted == False
            )
        )
        config = result.scalar_one_or_none()
        
        if not config:
            group_type = GroupType.SUPERGROUP if message.chat.type == "supergroup" else GroupType.GROUP
            config = GroupConfigModel.create_for_group(
                chat_id=message.chat.id,
                chat_title=message.chat.title,
                chat_username=message.chat.username,
                group_type=group_type,
                configured_by_user_id=message.from_user.id
            )
            session.add(config)
        
        # 启用消息保存
        config.is_message_save_enabled = True
        config.message_save_mode = MessageSaveMode.ALL
        
        await session.commit()
        
        await message.reply(
            "✅ **消息保存已启用**\n\n"
            "现在将自动保存此群组的所有消息。\n"
            "使用 `/group_config` 查看详细配置。",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"启用消息保存失败: {e}")
        await message.reply("❌ 启用失败，请稍后重试。")


@router.message(Command("save_disable"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]), AdminFilter())
async def cmd_save_disable(message: types.Message, session: AsyncSession) -> None:
    """
    快速禁用消息保存命令
    
    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    try:
        # 获取群组配置
        result = await session.execute(
            select(GroupConfigModel).where(
                GroupConfigModel.chat_id == message.chat.id,
                GroupConfigModel.is_deleted == False
            )
        )
        config = result.scalar_one_or_none()
        
        if config:
            # 禁用消息保存
            config.is_message_save_enabled = False
            config.message_save_mode = MessageSaveMode.DISABLED
            
            await session.commit()
            
            await message.reply(
                "❌ **消息保存已禁用**\n\n"
                "已停止保存此群组的消息。\n"
                "使用 `/save_enable` 重新启用。",
                parse_mode="Markdown"
            )
        else:
            await message.reply("ℹ️ 此群组尚未配置消息保存功能。")
        
    except Exception as e:
        logger.error(f"禁用消息保存失败: {e}")
        await message.reply("❌ 禁用失败，请稍后重试。")


# 导出路由器
__all__ = ["router", "GroupConfigStates"]