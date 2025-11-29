"""
群组配置内联键盘模块

本模块定义了群组消息保存配置相关的内联键盘,
用于群组配置管理界面的交互。

作者: Telegram Bot Template
创建时间: 2025-01-21
最后更新: 2025-01-21
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_group_config_keyboard(config_id: int) -> InlineKeyboardMarkup:
    """
    获取群组配置主键盘

    Args:
        config_id: 群组配置ID

    Returns:
        InlineKeyboardMarkup: 群组配置键盘
    """
    builder = InlineKeyboardBuilder()

    # 第一行: 启用/禁用 和 保存模式
    builder.row(
        InlineKeyboardButton(text="🔄 切换启用状态", callback_data=f"group_config:toggle_enable:{config_id}"),
        InlineKeyboardButton(text="⚙️ 保存模式", callback_data=f"group_config:change_mode:{config_id}"),
    )

    # 第二行: 消息类型过滤
    builder.row(
        InlineKeyboardButton(text="📝 文本消息", callback_data=f"group_config:toggle_text:{config_id}"),
        InlineKeyboardButton(text="🖼️ 媒体消息", callback_data=f"group_config:toggle_media:{config_id}"),
    )

    # 第三行: 特殊消息过滤
    builder.row(
        InlineKeyboardButton(text="↩️ 转发消息", callback_data=f"group_config:toggle_forwarded:{config_id}"),
        InlineKeyboardButton(text="💬 回复消息", callback_data=f"group_config:toggle_reply:{config_id}"),
    )

    # 第四行: 机器人消息
    builder.row(InlineKeyboardButton(text="🤖 机器人消息", callback_data=f"group_config:toggle_bot:{config_id}"))

    # 第五行: 管理操作
    builder.row(
        InlineKeyboardButton(text="🗑️ 清空消息", callback_data=f"group_config:clear_messages:{config_id}"),
        InlineKeyboardButton(text="🔄 刷新", callback_data=f"group_config:refresh:{config_id}"),
    )

    return builder.as_markup()


def get_save_mode_keyboard(config_id: int) -> InlineKeyboardMarkup:
    """
    获取保存模式选择键盘

    Args:
        config_id: 群组配置ID

    Returns:
        InlineKeyboardMarkup: 保存模式选择键盘
    """
    builder = InlineKeyboardBuilder()

    # 保存模式选项
    builder.row(InlineKeyboardButton(text="📋 保存所有消息", callback_data=f"save_mode:all:{config_id}"))

    builder.row(
        InlineKeyboardButton(text="📝 仅保存文本", callback_data=f"save_mode:text_only:{config_id}"),
        InlineKeyboardButton(text="🖼️ 仅保存媒体", callback_data=f"save_mode:media_only:{config_id}"),
    )

    builder.row(InlineKeyboardButton(text="⭐ 仅保存重要消息", callback_data=f"save_mode:important_only:{config_id}"))

    builder.row(InlineKeyboardButton(text="❌ 禁用保存", callback_data=f"save_mode:disabled:{config_id}"))

    # 返回按钮
    builder.row(
        InlineKeyboardButton(text="⬅️ 返回上一级", callback_data=f"group_config_back:{config_id}"),
        InlineKeyboardButton(text="↩️ 返回主面板", callback_data="home:back"),
    )

    return builder.as_markup()


def get_confirm_keyboard(confirm_callback: str, cancel_callback: str) -> InlineKeyboardMarkup:
    """
    获取确认操作键盘

    Args:
        confirm_callback: 确认回调数据
        cancel_callback: 取消回调数据

    Returns:
        InlineKeyboardMarkup: 确认操作键盘
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ 确认", callback_data=confirm_callback),
        InlineKeyboardButton(text="❌ 取消", callback_data=cancel_callback),
    )

    return builder.as_markup()


def get_message_export_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """
    获取消息导出键盘

    Args:
        chat_id: 群组聊天ID

    Returns:
        InlineKeyboardMarkup: 消息导出键盘
    """
    builder = InlineKeyboardBuilder()

    # 导出选项
    builder.row(
        InlineKeyboardButton(text="📄 导出为TXT", callback_data=f"export:txt:{chat_id}"),
        InlineKeyboardButton(text="📊 导出为CSV", callback_data=f"export:csv:{chat_id}"),
    )

    builder.row(InlineKeyboardButton(text="📋 导出为JSON", callback_data=f"export:json:{chat_id}"))

    # 时间范围选项
    builder.row(
        InlineKeyboardButton(text="📅 最近7天", callback_data=f"export_range:7d:{chat_id}"),
        InlineKeyboardButton(text="📅 最近30天", callback_data=f"export_range:30d:{chat_id}"),
    )

    builder.row(InlineKeyboardButton(text="📅 全部消息", callback_data=f"export_range:all:{chat_id}"))

    return builder.as_markup()


def get_message_filter_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """
    获取消息过滤键盘

    Args:
        chat_id: 群组聊天ID

    Returns:
        InlineKeyboardMarkup: 消息过滤键盘
    """
    builder = InlineKeyboardBuilder()

    # 消息类型过滤
    builder.row(
        InlineKeyboardButton(text="📝 文本消息", callback_data=f"filter:text:{chat_id}"),
        InlineKeyboardButton(text="🖼️ 图片消息", callback_data=f"filter:photo:{chat_id}"),
    )

    builder.row(
        InlineKeyboardButton(text="🎥 视频消息", callback_data=f"filter:video:{chat_id}"),
        InlineKeyboardButton(text="🎵 音频消息", callback_data=f"filter:audio:{chat_id}"),
    )

    builder.row(
        InlineKeyboardButton(text="📎 文档消息", callback_data=f"filter:document:{chat_id}"),
        InlineKeyboardButton(text="↩️ 转发消息", callback_data=f"filter:forwarded:{chat_id}"),
    )

    builder.row(
        InlineKeyboardButton(text="💬 回复消息", callback_data=f"filter:reply:{chat_id}"),
        InlineKeyboardButton(text="🤖 机器人消息", callback_data=f"filter:bot:{chat_id}"),
    )

    # 清除过滤器
    builder.row(InlineKeyboardButton(text="🔄 清除过滤器", callback_data=f"filter:clear:{chat_id}"))

    return builder.as_markup()


def get_pagination_keyboard(
    current_page: int, total_pages: int, callback_prefix: str, chat_id: int
) -> InlineKeyboardMarkup:
    """
    获取分页键盘

    Args:
        current_page: 当前页码
        total_pages: 总页数
        callback_prefix: 回调前缀
        chat_id: 群组聊天ID

    Returns:
        InlineKeyboardMarkup: 分页键盘
    """
    builder = InlineKeyboardBuilder()

    buttons = []

    # 上一页按钮
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(text="⬅️ 上一页", callback_data=f"{callback_prefix}:prev:{current_page - 1}:{chat_id}")
        )

    # 页码信息
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))

    # 下一页按钮
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="下一页 ➡️", callback_data=f"{callback_prefix}:next:{current_page + 1}:{chat_id}")
        )

    if buttons:
        builder.row(*buttons)

    return builder.as_markup()


# 导出所有函数
__all__ = [
    "get_confirm_keyboard",
    "get_group_config_keyboard",
    "get_message_export_keyboard",
    "get_message_filter_keyboard",
    "get_pagination_keyboard",
    "get_save_mode_keyboard",
]
