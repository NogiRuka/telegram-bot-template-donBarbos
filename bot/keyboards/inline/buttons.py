from aiogram.types import InlineKeyboardButton

from bot.keyboards.inline.constants import *

# ===== 用户功能 =====
PROFILE_BUTTON = InlineKeyboardButton(text=PROFILE_LABEL, callback_data=PROFILE_CALLBACK_DATA)
ACCOUNT_CENTER_BUTTON = InlineKeyboardButton(text=ACCOUNT_CENTER_LABEL, callback_data=ACCOUNT_CENTER_CALLBACK_DATA)
START_REGISTER_BUTTON = InlineKeyboardButton(text=START_REGISTER_LABEL, callback_data=START_REGISTER_CALLBACK_DATA)
CANCEL_REGISTER_BUTTON = InlineKeyboardButton(text=CANCEL_REGISTER_LABEL, callback_data=CANCEL_REGISTER_CALLBACK_DATA)

USER_INFO_BUTTON = InlineKeyboardButton(text=USER_INFO_LABEL, callback_data=USER_INFO_CALLBACK_DATA)
USER_LINES_BUTTON = InlineKeyboardButton(text=USER_LINES_LABEL, callback_data=USER_LINES_CALLBACK_DATA)
USER_DEVICES_BUTTON = InlineKeyboardButton(text=USER_DEVICES_LABEL, callback_data=USER_DEVICES_CALLBACK_DATA)
USER_PASSWORD_BUTTON = InlineKeyboardButton(text=USER_PASSWORD_LABEL, callback_data=USER_PASSWORD_CALLBACK_DATA)
USER_TAGS_BUTTON = InlineKeyboardButton(text=USER_TAGS_LABEL, callback_data=USER_TAGS_CALLBACK_DATA)
BACK_TO_ACCOUNT_BUTTON = InlineKeyboardButton(text=BACK_TO_ACCOUNT_LABEL, callback_data=BACK_TO_ACCOUNT_CALLBACK_DATA)

# ===== 管理员功能 =====
ADMIN_PANEL_BUTTON = InlineKeyboardButton(text=ADMIN_PANEL_LABEL, callback_data=ADMIN_PANEL_CALLBACK_DATA)

BACK_TO_ADMIN_PANEL_BUTTON = InlineKeyboardButton(text=BACK_TO_ADMIN_PANEL_LABEL, callback_data=BACK_TO_ADMIN_PANEL_CALLBACK_DATA)

# ===== 所有者功能 =====
OWNER_PANEL_BUTTON = InlineKeyboardButton(text=OWNER_PANEL_LABEL, callback_data=OWNER_PANEL_CALLBACK_DATA)

BACK_TO_OWNER_PANEL_BUTTON = InlineKeyboardButton(text=BACK_TO_OWNER_PANEL_LABEL, callback_data=BACK_TO_OWNER_PANEL_CALLBACK_DATA)


# ===== 通用导航 =====
BACK_TO_HOME_BUTTON = InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data=BACK_TO_HOME_CALLBACK_DATA)