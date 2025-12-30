from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def quiz_admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ 添加题目 (快捷)", callback_data="quiz_admin:add_quick"),
        InlineKeyboardButton(text="⚙️ 触发设置", callback_data="quiz_admin:settings")
    )
    builder.row(
        InlineKeyboardButton(text="📋 题目列表", callback_data="quiz_admin:list_questions"),
        InlineKeyboardButton(text="🖼️ 题图列表", callback_data="quiz_admin:list_images")
    )
    builder.row(
        InlineKeyboardButton(text="🧪 题目测试 (发给我)", callback_data="quiz_admin:test_trigger")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 返回管理面板", callback_data="admin:home")
    )
    return builder.as_markup()

def quiz_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎲 修改触发概率", callback_data="quiz_admin:set:probability"),
        InlineKeyboardButton(text="⏳ 修改冷却时间", callback_data="quiz_admin:set:cooldown")
    )
    builder.row(
        InlineKeyboardButton(text="🔢 修改每日上限", callback_data="quiz_admin:set:daily_limit"),
        InlineKeyboardButton(text="⏱️ 修改答题限时", callback_data="quiz_admin:set:timeout")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 返回问答菜单", callback_data="quiz_admin:menu")
    )
    return builder.as_markup()
