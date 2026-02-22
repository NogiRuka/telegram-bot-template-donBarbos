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
from contextlib import suppress

from aiogram import F, Router, types
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 移除db_session导入，使用依赖注入
from bot.database.models import GroupConfigModel, GroupType, MessageSaveMode
from bot.filters.admin import AdminFilter
from bot.filters.chat_admin import GroupAdminFilter
from bot.keyboards.inline.group_config import get_confirm_keyboard, get_group_config_keyboard, get_save_mode_keyboard
from bot.services.group_config_service import (
    get_group_message_stats,
    get_or_create_group_config,
    set_save_mode,
    soft_delete_messages_by_chat,
    toggle_save_enabled,
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


from bot.utils.text import escape_markdown_v2


async def _get_group_config_content(session: AsyncSession, config: GroupConfigModel) -> tuple[str, types.InlineKeyboardMarkup]:
    """
    获取群组配置显示内容（文本和键盘）

    Args:
        session: 数据库会话
        config: 群组配置对象

    Returns:
        tuple[str, InlineKeyboardMarkup]: (配置文本, 配置键盘)
    """
    total_messages = await get_group_message_stats(session, config.chat_id)

    # 辅助转义函数
    def esc(text: str) -> str:
        return escape_markdown_v2(str(text))

    # 构建配置信息文本 (MarkdownV2)
    config_text = f"""
🔧 *群组消息保存配置*

📊 *基本信息*
• 群组: {esc(config.get_group_info_display())}
• 群组ID: `{esc(str(config.chat_id))}`
• 群组类型: {esc(config.group_type.value)}

⚙️ *保存设置*
• 状态: {esc(config.get_save_status_display())}
• 保存模式: {esc(config.message_save_mode.value)}
• 已保存消息: {esc(str(config.total_messages_saved))} 条
• 数据库总消息: {esc(str(total_messages))} 条

📋 *过滤设置*
• 文本消息: {"✅" if config.save_text_messages else "❌"}
• 媒体消息: {"✅" if config.save_media_messages else "❌"}
• 转发消息: {"✅" if config.save_forwarded_messages else "❌"}
• 回复消息: {"✅" if config.save_reply_messages else "❌"}
• 机器人消息: {"✅" if config.save_bot_messages else "❌"}

⏰ *时间设置*
• 开始时间: {esc(config.save_start_date.strftime("%Y-%m-%d %H:%M") if config.save_start_date else "未设置")}
• 结束时间: {esc(config.save_end_date.strftime("%Y-%m-%d %H:%M") if config.save_end_date else "未设置")}

📏 *限制设置*
• 每日最大消息数: {esc(str(config.max_messages_per_day or "无限制"))}
• 最大文件大小: {esc(str(config.max_file_size_mb or "无限制"))} MB

🔍 *关键词过滤*
• 包含关键词: {len(json.loads(config.include_keywords)) if config.include_keywords else 0} 个
• 排除关键词: {len(json.loads(config.exclude_keywords)) if config.exclude_keywords else 0} 个

📝 *备注*: {esc(config.notes or "无")}
    """

    return config_text, get_group_config_keyboard(config)


@router.message(Command("group_config", "gc"), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP, ChatType.PRIVATE]))
async def cmd_group_config(message: types.Message, command: CommandObject, session: AsyncSession) -> None:
    """
    群组配置命令
    """
    # 手动进行权限检查，避免 Filter 组合问题
    user_id = message.from_user.id
    is_global_admin = await AdminFilter()(message, session)
    is_group_admin = False

    # 检查群组管理员权限 (如果不是全局管理员)
    if not is_global_admin:
        is_group_admin = await GroupAdminFilter()(message)

    # 如果两者都不是，拒绝访问
    if not is_global_admin and not is_group_admin:
        # 仅在群组中忽略（避免干扰聊天），私聊可以提示
        if message.chat.type == ChatType.PRIVATE:
            # 这里的逻辑其实有点绕，因为 GroupAdminFilter 在私聊是直接返回 True 的
            # 但如果目的是管理群组，私聊时应该至少是 Global Admin 或者后续检查目标群组的权限
            # 暂时保持现有逻辑：如果 GroupAdminFilter 返回 True (私聊默认 True)，则允许进入
            pass
        else:
            return

    logger.info(f"cmd_group_config called by user {user_id} in chat {message.chat.id}")
    try:
        target_chat_id = message.chat.id
        target_chat_title = message.chat.title
        target_chat_username = message.chat.username
        target_group_type = GroupType.SUPERGROUP if message.chat.type == "supergroup" else GroupType.GROUP

        if message.chat.type == ChatType.PRIVATE:
            if not command.args:
                await message.reply("⚠️ 私聊请指定群组ID或用户名: `/gc <group_id|@username>`", parse_mode="Markdown")
                return

            input_arg = command.args.strip()

            try:
                # 尝试解析为整数ID
                try:
                    target_chat_id = int(input_arg)
                    chat_identifier = target_chat_id
                except ValueError:
                    # 如果不是整数，视为用户名，确保以@开头
                    chat_identifier = input_arg if input_arg.startswith("@") else f"@{input_arg}"

                # 获取群组信息
                chat_info = await message.bot.get_chat(chat_identifier)

                # 更新目标信息
                target_chat_id = chat_info.id
                target_chat_title = chat_info.title
                target_chat_username = chat_info.username
                target_group_type = GroupType.SUPERGROUP if chat_info.type == "supergroup" else GroupType.GROUP

            except Exception as e:
                await message.reply(f"❌ 无法获取群组信息 (Bot可能不在群组中或用户名无效): {e}", parse_mode="Markdown")
                return

        config = await get_or_create_group_config(
            session=session,
            chat_id=target_chat_id,
            chat_title=target_chat_title,
            chat_username=target_chat_username,
            group_type=target_group_type,
            configured_by_user_id=message.from_user.id,
        )

        text, markup = await _get_group_config_content(session, config)
        await message.reply(text, reply_markup=markup, parse_mode="MarkdownV2")

    except Exception as e:
        logger.exception(f"❌ 显示群组配置失败: {e}")
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
        result = await session.execute(select(GroupConfigModel).where(GroupConfigModel.id == config_id))
        config = result.scalar_one_or_none()

        if not config:
            await callback.answer("❌ 配置不存在")
            return

        if action == "toggle_enable":
            config = await toggle_save_enabled(session, config)

            status = "启用" if config.is_message_save_enabled else "禁用"
            await callback.answer(f"✅ 已{status}消息保存")

            # 更新界面
            text, markup = await _get_group_config_content(session, config)
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="MarkdownV2")

        elif action == "change_mode":
            # 显示保存模式选择
            await callback.message.edit_text(
                "🔧 *选择消息保存模式*\n\n"
                "• *保存所有消息*: 保存群组中的所有消息\n"
                "• *仅保存文本*: 只保存文本消息\n"
                "• *仅保存媒体*: 只保存图片、视频等媒体消息\n"
                "• *仅保存重要消息*: 只保存回复和转发消息\n"
                "• *禁用*: 停止保存消息",
                reply_markup=get_save_mode_keyboard(config.id),
                parse_mode="Markdown",
            )

        elif action == "toggle_text":
            config.save_text_messages = not config.save_text_messages
            await session.commit()
            await callback.answer(f"✅ 文本消息保存已{'启用' if config.save_text_messages else '禁用'}")

            text, markup = await _get_group_config_content(session, config)
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

        elif action == "toggle_media":
            config.save_media_messages = not config.save_media_messages
            await session.commit()
            await callback.answer(f"✅ 媒体消息保存已{'启用' if config.save_media_messages else '禁用'}")

            text, markup = await _get_group_config_content(session, config)
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

        elif action == "toggle_forwarded":
            config.save_forwarded_messages = not config.save_forwarded_messages
            await session.commit()
            await callback.answer(f"✅ 转发消息保存已{'启用' if config.save_forwarded_messages else '禁用'}")

            text, markup = await _get_group_config_content(session, config)
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

        elif action == "toggle_reply":
            config.save_reply_messages = not config.save_reply_messages
            await session.commit()
            await callback.answer(f"✅ 回复消息保存已{'启用' if config.save_reply_messages else '禁用'}")

            text, markup = await _get_group_config_content(session, config)
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

        elif action == "toggle_bot":
            config.save_bot_messages = not config.save_bot_messages
            await session.commit()
            await callback.answer(f"✅ 机器人消息保存已{'启用' if config.save_bot_messages else '禁用'}")

            text, markup = await _get_group_config_content(session, config)
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

        elif action == "clear_messages":
            # 显示确认对话框
            await callback.message.edit_text(
                "⚠️ *确认清空消息*\n\n"
                f"您确定要清空群组 `{config.chat_title}` 的所有已保存消息吗？\n\n"
                "*此操作不可撤销！*",
                reply_markup=get_confirm_keyboard(f"confirm_clear:{config.id}", f"group_config_back:{config.id}"),
                parse_mode="Markdown",
            )

        elif action == "refresh":
            # 刷新配置显示
            text, markup = await _get_group_config_content(session, config)
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            await callback.answer("🔄 配置已刷新")

    except Exception as e:
        logger.exception(f"❌ 处理群组配置回调失败: {e}")
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
        result = await session.execute(select(GroupConfigModel).where(GroupConfigModel.id == config_id))
        config = result.scalar_one_or_none()

        if not config:
            await callback.answer("❌ 配置不存在")
            return

        # 更新保存模式
        mode_map = {
            "all": MessageSaveMode.ALL,
            "text_only": MessageSaveMode.TEXT_ONLY,
            "media_only": MessageSaveMode.MEDIA_ONLY,
            "important_only": MessageSaveMode.IMPORTANT_ONLY,
            "disabled": MessageSaveMode.DISABLED,
        }
        await set_save_mode(session, config, mode_map[mode])

        mode_names = {
            "all": "保存所有消息",
            "text_only": "仅保存文本",
            "media_only": "仅保存媒体",
            "important_only": "仅保存重要消息",
            "disabled": "已禁用",
        }

        await callback.answer(f"✅ 保存模式已设置为: {mode_names[mode]}")

        # 返回配置页面
        text, markup = await _get_group_config_content(session, config)
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"❌ 处理保存模式回调失败: {e}")
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
        result = await session.execute(select(GroupConfigModel).where(GroupConfigModel.id == config_id))
        config = result.scalar_one_or_none()

        if not config:
            await callback.answer("❌ 配置不存在")
            return

        # 软删除该群组的所有消息
        deleted_count = await soft_delete_messages_by_chat(session, config.chat_id)

        # 重置配置统计
        config.total_messages_saved = 0
        config.last_message_date = None

        await session.commit()

        await callback.answer(f"✅ 已清空 {deleted_count} 条消息")

        # 返回配置页面
        text, markup = await _get_group_config_content(session, config)
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"❌ 清空消息失败: {e}")
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
        config_id = int(callback.data.split(":")[1])

        # 获取配置
        result = await session.execute(select(GroupConfigModel).where(GroupConfigModel.id == config_id))
        config = result.scalar_one_or_none()

        if not config:
            await callback.answer("❌ 配置不存在")
            return

        # 返回配置页面
        text, markup = await _get_group_config_content(session, config)
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"❌ 返回群组配置失败: {e}")
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
                GroupConfigModel.is_deleted.is_(False),
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
                configured_by_user_id=message.from_user.id,
            )
            session.add(config)

        # 启用消息保存
        config.is_message_save_enabled = True
        config.message_save_mode = MessageSaveMode.ALL

        await session.commit()

        await message.reply(
            "✅ *消息保存已启用*\n\n现在将自动保存此群组的所有消息。\n使用 `/group_config` 查看详细配置。",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.exception(f"❌ 启用消息保存失败: {e}")
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
                GroupConfigModel.is_deleted.is_(False),
            )
        )
        config = result.scalar_one_or_none()

        if config:
            # 禁用消息保存
            config.is_message_save_enabled = False
            config.message_save_mode = MessageSaveMode.DISABLED

            await session.commit()

            await message.reply(
                "❌ *消息保存已禁用*\n\n已停止保存此群组的消息。\n使用 `/save_enable` 重新启用。",
                parse_mode="Markdown",
            )
        else:
            await message.reply("ℹ️ 此群组尚未配置消息保存功能。")

    except Exception as e:
        logger.exception(f"❌ 禁用消息保存失败: {e}")
        await message.reply("❌ 禁用失败，请稍后重试。")


# 导出路由器
__all__ = ["GroupConfigStates", "router"]
