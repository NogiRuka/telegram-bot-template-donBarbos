from aiogram.types import InlineKeyboardButton

from bot.keyboards.inline.labels import (
    ACCOUNT_CENTER_LABEL,
    ADMIN_PANEL_LABEL,
    BACK_LABEL,
    BACK_TO_HOME_LABEL,
    OWNER_PANEL_LABEL,
    PROFILE_LABEL,
    START_REGISTER_LABEL,
    USER_DEVICES_LABEL,
    USER_INFO_LABEL,
    USER_LINES_LABEL,
    USER_PASSWORD_LABEL,
)

PROFILE_BUTTON = InlineKeyboardButton(text=PROFILE_LABEL, callback_data="user:profile")
ACCOUNT_CENTER_BUTTON = InlineKeyboardButton(text=ACCOUNT_CENTER_LABEL, callback_data="user:account")
ADMIN_PANEL_BUTTON = InlineKeyboardButton(text=ADMIN_PANEL_LABEL, callback_data="admin:panel")
OWNER_PANEL_BUTTON = InlineKeyboardButton(text=OWNER_PANEL_LABEL, callback_data="owner:panel")
BACK_TO_HOME_BUTTON = InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back")
BACK_BUTTON = InlineKeyboardButton(text=BACK_LABEL, callback_data="owner:panel")
START_REGISTER_BUTTON = InlineKeyboardButton(text=START_REGISTER_LABEL, callback_data="user:register")
USER_INFO_BUTTON = InlineKeyboardButton(text=USER_INFO_LABEL, callback_data="user:info")
USER_LINES_BUTTON = InlineKeyboardButton(text=USER_LINES_LABEL, callback_data="user:lines")
USER_DEVICES_BUTTON = InlineKeyboardButton(text=USER_DEVICES_LABEL, callback_data="user:devices")
USER_PASSWORD_BUTTON = InlineKeyboardButton(text=USER_PASSWORD_LABEL, callback_data="user:password")
