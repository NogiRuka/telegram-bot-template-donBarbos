from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.buttons import (
    BACK_TO_ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
    BACK_TO_QUIZ_ADMIN_BUTTON
)
from bot.keyboards.inline.constants import (
    QUIZ_ADMIN_ADD_QUICK_CALLBACK_DATA,
    QUIZ_ADMIN_ADD_QUICK_LABEL,
    QUIZ_ADMIN_LIST_IMAGES_CALLBACK_DATA,
    QUIZ_ADMIN_LIST_IMAGES_LABEL,
    QUIZ_ADMIN_LIST_QUESTIONS_CALLBACK_DATA,
    QUIZ_ADMIN_LIST_QUESTIONS_LABEL,
    QUIZ_ADMIN_SETTINGS_CALLBACK_DATA,
    QUIZ_ADMIN_SETTINGS_LABEL,
    QUIZ_ADMIN_TEST_TRIGGER_CALLBACK_DATA,
    QUIZ_ADMIN_TEST_TRIGGER_LABEL,
    QUIZ_ADMIN_SET_COOLDOWN,
    QUIZ_ADMIN_SET_COOLDOWN_LABEL,
    QUIZ_ADMIN_SET_DAILY_LIMIT,
    QUIZ_ADMIN_SET_DAILY_LIMIT_LABEL,
    QUIZ_ADMIN_SET_PROBABILITY,
    QUIZ_ADMIN_SET_PROBABILITY_LABEL,
    QUIZ_ADMIN_SET_TIMEOUT,
    QUIZ_ADMIN_SET_TIMEOUT_LABEL,
)

def quiz_admin_menu_kb() -> InlineKeyboardMarkup:
    """问答管理菜单键盘"""
    buttons = [
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_ADD_QUICK_LABEL, callback_data=QUIZ_ADMIN_ADD_QUICK_CALLBACK_DATA),
            InlineKeyboardButton(text=QUIZ_ADMIN_SETTINGS_LABEL, callback_data=QUIZ_ADMIN_SETTINGS_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_LIST_QUESTIONS_LABEL, callback_data=QUIZ_ADMIN_LIST_QUESTIONS_CALLBACK_DATA),
            InlineKeyboardButton(text=QUIZ_ADMIN_LIST_IMAGES_LABEL, callback_data=QUIZ_ADMIN_LIST_IMAGES_CALLBACK_DATA)
        ],
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_TEST_TRIGGER_LABEL, callback_data=QUIZ_ADMIN_TEST_TRIGGER_CALLBACK_DATA)
        ],
        [BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()

def quiz_settings_kb() -> InlineKeyboardMarkup:
    """问答设置键盘"""
    buttons = [
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_PROBABILITY_LABEL, callback_data=QUIZ_ADMIN_SET_PROBABILITY),
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_COOLDOWN_LABEL, callback_data=QUIZ_ADMIN_SET_COOLDOWN)
        ],
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_DAILY_LIMIT_LABEL, callback_data=QUIZ_ADMIN_SET_DAILY_LIMIT),
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_TIMEOUT_LABEL, callback_data=QUIZ_ADMIN_SET_TIMEOUT)
        ],
        [BACK_TO_QUIZ_ADMIN_BUTTON]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()
