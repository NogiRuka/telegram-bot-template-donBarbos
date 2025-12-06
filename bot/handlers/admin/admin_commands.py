"""
管理员命令处理器模块(子包)
"""

import contextlib
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models import GroupConfigModel, GroupType, MessageModel, MessageSaveMode
from bot.database.models.config import ConfigType
from bot.keyboards.inline.group_config import get_confirm_keyboard
from bot.services.config_service import (
    get_config,
    get_free_registration_status,
    get_registration_window,
    is_registration_open,
    set_config,
    set_free_registration_status,
    set_registration_window,
)
from bot.services.message_export import MessageExportService
from bot.utils.permissions import require_admin_feature, require_admin_priv, require_owner

router = Router(name="admin_commands")
MAX_MESSAGE_LENGTH = 4000
SUMMARY_LIMIT = 20


def has_admin_priv(role: str) -> bool:
    """判断是否具有管理员或所有者权限

    功能说明:
    - 基于鉴权中间件注入的 `role` 判定是否拥有管理权限

    输入参数:
    - role: 角色标识字符串("user" | "admin" | "owner")

    返回值:
    - bool: True 表示允许执行管理员级操作
    """
    return role in {"admin", "owner"}


def is_owner(role: str) -> bool:
    """判断是否为所有者

    功能说明:
    - 检查角色是否为 `owner`

    输入参数:
    - role: 角色标识字符串

    返回值:
    - bool: True 表示为所有者
    """
    return role == "owner"


@router.message(Command("admin_help"))
@require_admin_priv
async def admin_help_command(message: Message) -> None:
    """管理员帮助命令

    功能说明:
    - 展示管理员/所有者可用的命令列表与说明

    输入参数:
    - message: 文本消息对象

    返回值:
    - None
    """
    help_text = """
🛡️ **管理员/所有者命令帮助**

**群组管理:**
• `/admin_groups` - 查看所有群组配置
• `/admin_enable_group <chat_id>` - 启用群组消息保存
• `/admin_disable_group <chat_id>` - 禁用群组消息保存
• `/admin_group_info <chat_id>` - 查看群组详细信息

**数据管理:**
• `/admin_cleanup` - 清理过期数据
• `/admin_stats` - 查看全局统计
• `/admin_export_all` - 导出所有群组数据

**系统管理:**
• `/admin_broadcast <消息>` - 向所有群组广播消息
• `/admin_maintenance` - 进入维护模式
• `/admin_status` - 查看系统状态
• `/admin_open_registration [开始时间ISO] [持续分钟]` - 开启注册并可配置时间窗
• `/admin_close_registration` - 关闭注册
• `/admin_registration_status` - 查看注册开关与时间窗

**注意:** 管理员命令需管理员或所有者权限; 危险操作仅所有者可执行
    """
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("admin_groups"))
@require_admin_priv
@require_admin_feature("admin.groups")
async def admin_groups_command(message: Message, session: AsyncSession) -> None:
    """查看所有群组配置

    功能说明:
    - 查询并展示群组配置与统计信息(长度过长时展示摘要)

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        query = select(GroupConfigModel).order_by(GroupConfigModel.created_at.desc())
        result = await session.execute(query)
        configs = result.scalars().all()
        if not configs:
            await message.answer("📋 暂无群组配置")
            return
        groups_text = "📋 **所有群组配置**\n\n"
        for config in configs:
            status = "🟢 启用" if config.is_message_save_enabled else "🔴 禁用"
            group_type = "超级群组" if config.group_type == GroupType.SUPERGROUP else "普通群组"
            groups_text += f"**群组 {config.chat_id}**\n"
            groups_text += f"  状态: {status}\n"
            groups_text += f"  类型: {group_type}\n"
            groups_text += f"  保存模式: {config.message_save_mode.value}\n"
            groups_text += f"  已保存消息: {config.total_messages_saved}\n"
            groups_text += f"  创建时间: {config.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        if len(groups_text) > MAX_MESSAGE_LENGTH:
            groups_text = "📋 **所有群组配置**\n\n"
            enabled_count = sum(1 for c in configs if c.is_message_save_enabled)
            total_messages = sum(c.total_messages_saved for c in configs)
            groups_text += "📊 **统计信息:**\n"
            groups_text += f"  总群组数: {len(configs)}\n"
            groups_text += f"  启用群组: {enabled_count}\n"
            groups_text += f"  禁用群组: {len(configs) - enabled_count}\n"
            groups_text += f"  总消息数: {total_messages}\n\n"
            groups_text += "📝 **群组列表:**\n"
            for config in configs[:SUMMARY_LIMIT]:
                status = "🟢" if config.is_message_save_enabled else "🔴"
                groups_text += f"  {status} 群组 {config.chat_id} ({config.total_messages_saved} 条消息)\n"
            if len(configs) > SUMMARY_LIMIT:
                groups_text += f"\n... 还有 {len(configs) - SUMMARY_LIMIT} 个群组"
        await message.answer(groups_text, parse_mode="Markdown")
    except SQLAlchemyError as e:
        logger.error(f"❌ 查看群组配置失败: {e}")
        await message.answer("🔴 查看群组配置时发生错误")


@router.message(Command("admin_enable_group"))
@require_admin_priv
@require_admin_feature("admin.groups")
async def admin_enable_group_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """启用群组消息保存

    功能说明:
    - 将指定群组的消息保存功能开启, 如无配置则创建默认配置

    输入参数:
    - message: 文本消息对象
    - command: 命令对象(包含 chat_id 参数)
    - session: 异步数据库会话

    返回值:
    - None
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


@router.message(Command("admin_disable_group"))
@require_admin_priv
@require_admin_feature("admin.groups")
async def admin_disable_group_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """禁用群组消息保存

    功能说明:
    - 将指定群组的消息保存功能关闭, 若群组未配置则提示

    输入参数:
    - message: 文本消息对象
    - command: 命令对象(包含 chat_id 参数)
    - session: 异步数据库会话

    返回值:
    - None
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


@router.message(Command("admin_group_info"))
@require_admin_priv
@require_admin_feature("admin.groups")
async def admin_group_info_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """查看群组详细信息

    功能说明:
    - 展示群组基本信息, 最近统计与累积统计

    输入参数:
    - message: 文本消息对象
    - command: 命令对象(包含 chat_id 参数)
    - session: 异步数据库会话

    返回值:
    - None
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
        info_text = f"📊 **群组 {chat_id} 详细信息**\n\n"
        status = "🟢 启用" if config.is_message_save_enabled else "🔴 禁用"
        group_type = "超级群组" if config.group_type == GroupType.SUPERGROUP else "普通群组"
        info_text += "**基本信息:**\n"
        info_text += f"  状态: {status}\n"
        info_text += f"  类型: {group_type}\n"
        info_text += f"  保存模式: {config.message_save_mode.value}\n"
        info_text += f"  创建时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        info_text += f"  更新时间: {config.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        info_text += "**过滤设置:**\n"
        info_text += f"  保存文本: {'🟢' if config.save_text else '🔴'}\n"
        info_text += f"  保存媒体: {'🟢' if config.save_media else '🔴'}\n"
        info_text += f"  保存转发: {'🟢' if config.save_forwarded else '🔴'}\n"
        info_text += f"  保存回复: {'🟢' if config.save_replies else '🔴'}\n"
        info_text += f"  保存机器人: {'🟢' if config.save_bot_messages else '🔴'}\n\n"
        if stats:
            info_text += "**统计信息(最近30天):**\n"
            info_text += f"  总消息数: {stats.get('total_messages', 0)}\n"
            info_text += f"  活跃用户: {len(stats.get('top_users', []))}\n"
            if stats.get("message_types"):
                info_text += f"  消息类型: {len(stats['message_types'])} 种\n"
        info_text += "\n**历史统计:**\n"
        info_text += f"  累计消息: {config.total_messages_saved}\n"
        info_text += f"  累计用户: {config.total_users}\n"
        await message.answer(info_text, parse_mode="Markdown")
    except ValueError:
        await message.answer("🔴 无效的群组ID")
    except SQLAlchemyError as e:
        logger.error(f"❌ 查看群组信息失败: {e}")
        await message.answer("🔴 查看群组信息时发生错误")


@router.message(Command("admin_cleanup"))
@require_owner
async def admin_cleanup_command(message: Message, session: AsyncSession) -> None:
    """清理过期数据(所有者)

    功能说明:
    - 删除 90 天前的旧消息数据, 先展示确认提示

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        cleanup_date = datetime.now(timezone.utc) - timedelta(days=90)
        count_query = select(func.count(MessageModel.id)).where(MessageModel.created_at < cleanup_date)
        result = await session.execute(count_query)
        message_count = result.scalar() or 0
        if message_count == 0:
            await message.answer("🟢 没有需要清理的过期数据")
            return
        await message.answer(
            f"🗑️ **数据清理确认**\n\n将删除 {message_count} 条90天前的消息\n此操作不可撤销, 是否继续?",
            reply_markup=get_confirm_keyboard(f"admin_cleanup_confirm:{message_count}", "admin_cleanup_cancel"),
            parse_mode="Markdown",
        )
    except SQLAlchemyError as e:
        logger.error(f"❌ 数据清理失败: {e}")
        await message.answer("🔴 数据清理时发生错误")


@router.callback_query(F.data.startswith("admin_cleanup_confirm:"))
@require_owner
async def handle_cleanup_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    """确认清理过期数据(所有者)

    功能说明:
    - 执行过期数据删除并反馈结果

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        int(callback.data.split(":")[1])
        await callback.answer("🔄 正在清理数据...")
        cleanup_date = datetime.now(timezone.utc) - timedelta(days=90)
        delete_query = delete(MessageModel).where(MessageModel.created_at < cleanup_date)
        result = await session.execute(delete_query)
        await session.commit()
        deleted_count = result.rowcount
        await callback.message.edit_text(
            f"🟢 **数据清理完成**\n\n"
            f"已删除 {deleted_count} 条过期消息\n"
            f"清理时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown",
        )
    except (ValueError, SQLAlchemyError) as e:
        logger.error(f"❌ 确认清理失败: {e}")
        await callback.answer("🔴 清理失败", show_alert=True)


@router.callback_query(F.data == "admin_cleanup_cancel")
async def handle_cleanup_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🔴 已取消数据清理操作")
    await callback.answer("已取消")


@router.message(Command("admin_stats"))
@require_admin_feature("admin.stats")
async def admin_stats_command(message: Message, session: AsyncSession) -> None:
    if not is_super_admin(message.from_user.id):
        await message.answer("🔴 此命令仅限超级管理员使用")
        return
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
        stats_text = "📊 **全局统计信息**\n\n"
        stats_text += "**群组统计:**\n"
        stats_text += f"  总群组数: {total_groups}\n"
        stats_text += f"  启用群组: {enabled_groups}\n"
        stats_text += f"  禁用群组: {total_groups - enabled_groups}\n"
        stats_text += (
            f"  启用率: {(enabled_groups / total_groups * 100):.1f}%\n\n" if total_groups > 0 else "  启用率: 0%\n\n"
        )
        stats_text += "**消息统计:**\n"
        stats_text += f"  总消息数: {total_messages:,}\n"
        stats_text += f"  最近30天: {recent_messages:,}\n"
        stats_text += f"  日均消息: {recent_messages / 30:.1f}\n\n"
        stats_text += "**系统信息:**\n"
        stats_text += f"  统计时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
        stats_text += "  运行状态: 🟢 正常"
        await message.answer(stats_text, parse_mode="Markdown")
    except SQLAlchemyError as e:
        logger.error(f"❌ 查看全局统计失败: {e}")
        await message.answer("🔴 查看统计信息时发生错误")


__all__ = ["router"]


def is_super_admin(user_id: int) -> bool:
    """判断是否为超级管理员

    功能说明:
    - 将所有者视为超级管理员, 拥有最高权限

    输入参数:
    - user_id: Telegram 用户ID

    返回值:
    - bool: True 表示为超级管理员
    """
    with contextlib.suppress(Exception):
        return user_id == settings.get_owner_id()
    return False


@router.message(Command("admin_hitokoto"))
@require_admin_priv
@require_admin_feature("admin.hitokoto")
async def admin_hitokoto_command(message: Message, session: AsyncSession) -> None:
    """一言管理命令

    功能说明:
    - 管理配置 Hitokoto 分类参数, 支持多选并保存到配置表

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    categories = await get_config(session, "admin.hitokoto.categories") or []
    type_names: dict[str, str] = {
        "a": "动画",
        "b": "漫画",
        "c": "游戏",
        "d": "文学",
        "e": "原创",
        "f": "来自网络",
        "g": "其他",
        "h": "影视",
        "i": "诗词",
        "j": "网易云",
        "k": "哲学",
        "l": "抖机灵",
    }
    all_types = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for idx, ch in enumerate(all_types, start=1):
        enabled = ch in categories
        name = type_names.get(ch, ch)
        label = f"{name} {'🟢' if enabled else '🔴'}"
        current_row.append(InlineKeyboardButton(text=label, callback_data=f"admin:hitokoto:toggle:{ch}"))
        if idx % 4 == 0:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append(
        [
            InlineKeyboardButton(text="⬅️ 返回", callback_data="admin:panel"),
            InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"),
        ]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    current_names = [type_names.get(ch, ch) for ch in categories]
    desc = (
        "📝 一言管理\n\n"
        "选择需要纳入的分类参数(多选):\n"
        "a 动画 | b 漫画 | c 游戏 | d 文学 | e 原创\n"
        "f 来自网络 | g 其他 | h 影视 | i 诗词 | j 网易云\n"
        "k 哲学 | l 抖机灵\n\n"
        f"当前分类: {', '.join(current_names) if current_names else '未选择'}\n"
        "提示: 可多次点击切换, 选择会即时保存。"
    )
    await message.answer(desc, reply_markup=kb)


@router.callback_query(F.data.startswith("admin:hitokoto:toggle:"))
@require_admin_priv
@require_admin_feature("admin.hitokoto")
async def admin_hitokoto_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换一言分类

    功能说明:
    - 切换指定分类选中状态, 实时更新配置但不关闭面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        data = callback.data or ""
        ch = data.split(":")[-1]
        categories = await get_config(session, "admin.hitokoto.categories") or []
        if ch in categories:
            categories = [c for c in categories if c != ch]
        else:
            categories.append(ch)
        operator_id = callback.from_user.id if getattr(callback, "from_user", None) else None
        await set_config(
            session,
            "admin.hitokoto.categories",
            categories,
            ConfigType.LIST,
            operator_id=operator_id,
        )
        type_names: dict[str, str] = {
            "a": "动画",
            "b": "漫画",
            "c": "游戏",
            "d": "文学",
            "e": "原创",
            "f": "来自网络",
            "g": "其他",
            "h": "影视",
            "i": "诗词",
            "j": "网易云",
            "k": "哲学",
            "l": "抖机灵",
        }
        all_types = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
        rows: list[list[InlineKeyboardButton]] = []
        current_row: list[InlineKeyboardButton] = []
        for idx, t in enumerate(all_types, start=1):
            enabled = t in categories
            name = type_names.get(t, t)
            label = f"{name} {'🟢' if enabled else '🔴'}"
            current_row.append(InlineKeyboardButton(text=label, callback_data=f"admin:hitokoto:toggle:{t}"))
            if idx % 4 == 0:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)
        rows.append(
            [
                InlineKeyboardButton(text="⬅️ 返回", callback_data="admin:panel"),
                InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"),
            ]
        )
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        msg = callback.message
        if msg:
            await msg.edit_reply_markup(reply_markup=kb)
        await callback.answer("已更新分类")
    except (ValueError, TelegramBadRequest) as _:
        await callback.answer("操作失败", show_alert=True)


@router.callback_query(F.data == "admin:hitokoto:close")
@require_admin_priv
@require_admin_feature("admin.hitokoto")
async def admin_hitokoto_close(callback: CallbackQuery, session: AsyncSession) -> None:
    """保存并关闭一言管理面板

    功能说明:
    - 读取当前配置并提示保存完成, 关闭面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    cats: list[str] = await get_config(session, "admin.hitokoto.categories")
    await callback.answer(f"🟢 已保存分类: {', '.join(cats)}")


@router.message(Command("admin_open_registration"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def admin_open_registration_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """开启注册并设置时间窗

    功能说明:
    - 管理员开启注册开关, 可选设置开始时间与持续分钟
    - 命令格式: /admin_open_registration [开始时间ISO] [持续分钟]
    - 示例: /admin_open_registration 2025-06-25T12:00:00 120

    输入参数:
    - message: 文本消息对象
    - command: 命令对象，包含解析后的参数
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        # 解析命令参数
        args = (command.args or "").strip().split()
        start_iso: str | None = None
        duration_minutes: int | None = None

        # 第一个参数为开始时间（ISO格式）
        if len(args) >= 1:
            start_iso = args[0]
        # 第二个参数为持续分钟数
        if len(args) >= 2:
            try:
                duration_minutes = int(args[1])
            except ValueError:
                await message.answer("🔴 持续分钟数必须是整数")
                return

        # 设置注册窗口
        await set_registration_window(session, start_iso, duration_minutes, operator_id=message.from_user.id)
        # 获取最新窗口配置
        window = await get_registration_window(session) or {}
        start = window.get("start_iso") or datetime.now(timezone.utc).isoformat()
        dur = window.get("duration_minutes")

        # 构造回复文本
        text = "🟢 已配置注册时间窗\n"
        text += f"开始时间: {start}\n"
        text += f"持续分钟: {dur if dur is not None else '不限'}\n"
        text += f"自由注册: {'🟢 开启' if await get_free_registration_status(session) else '🔴 关闭'}"
        await message.answer(text)

    except SQLAlchemyError:
        logger.error("❌ 开启注册失败")
        await message.answer("🔴 开启注册失败")


@router.message(Command("admin_close_registration"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def admin_close_registration_command(message: Message, session: AsyncSession) -> None:
    """关闭注册

    功能说明:
    - 管理员关闭注册开关

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        await set_free_registration_status(session, False, operator_id=message.from_user.id)
        await set_registration_window(session, None, None, operator_id=message.from_user.id)
        await message.answer("🔴 已关闭自由注册并清除时间窗")
    except SQLAlchemyError:
        await message.answer("🔴 关闭注册失败")


@router.message(Command("admin_registration_status"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def admin_registration_status_command(message: Message, session: AsyncSession) -> None:
    """查看注册状态

    功能说明:
    - 显示注册开关与时间窗配置

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        open_flag = await is_registration_open(session)
        free_open = await get_free_registration_status(session)
        window = await get_registration_window(session) or {}
        start = window.get("start_iso")
        dur = window.get("duration_minutes")
        text = "📋 注册状态\n"
        text += f"开关: {'🟢 开启' if open_flag else '🔴 关闭'}\n"
        text += f"自由注册: {'🟢 开启' if free_open else '🔴 关闭'}\n"
        text += f"开始时间: {start or '未设置'}\n"
        text += f"持续分钟: {dur if dur is not None else '未设置'}"
        await message.answer(text)
    except SQLAlchemyError:
        await message.answer("🔴 获取注册状态失败")
@router.message(Command("admin_open_free_registration"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def admin_open_free_registration_command(message: Message, session: AsyncSession) -> None:
    """开启自由注册

    功能说明:
    - 设置 `registration.free_open = True`, 不修改时间窗

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        await set_free_registration_status(session, True, operator_id=message.from_user.id)
        await message.answer("🟢 已开启自由注册")
    except SQLAlchemyError:
        await message.answer("🔴 开启自由注册失败")


@router.message(Command("admin_close_free_registration"))
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def admin_close_free_registration_command(message: Message, session: AsyncSession) -> None:
    """关闭自由注册

    功能说明:
    - 设置 `registration.free_open = False`

    输入参数:
    - message: 文本消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        await set_free_registration_status(session, False, operator_id=message.from_user.id)
        await message.answer("🔴 已关闭自由注册")
    except SQLAlchemyError:
        await message.answer("🔴 关闭自由注册失败")
