from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.keyboards.inline.labels import (
    PROFILE_LABEL,
    ACCOUNT_CENTER_LABEL,
    USER_INFO_LABEL,
    USER_LINES_LABEL,
    USER_DEVICES_LABEL,
    USER_PASSWORD_LABEL,
    START_REGISTER_LABEL,
    BACK_TO_HOME_LABEL,
)


def build_user_home_rows() -> list[list[InlineKeyboardButton]]:
    """用户首页行构建

    功能说明:
    - 返回用户首页的基础按钮行集合, 供其它角色组合复用

    输入参数:
    - 无

    返回值:
    - list[list[InlineKeyboardButton]]: 按钮行集合
    """
    return [
        [
            InlineKeyboardButton(text=PROFILE_LABEL, callback_data="user:profile"),
            InlineKeyboardButton(text=ACCOUNT_CENTER_LABEL, callback_data="user:account"),
        ],
    ]


def make_home_keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    """首页键盘生成器

    功能说明:
    - 将按钮行集合转换为内联键盘, 统一布局规则

    输入参数:
    - rows: 按钮行集合

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    kb = InlineKeyboardBuilder(markup=rows)
    return kb.as_markup()


def get_start_user_keyboard() -> InlineKeyboardMarkup:
    """用户首页键盘

    功能说明:
    - 提供一级入口: 个人信息与账号中心

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    return make_home_keyboard(build_user_home_rows())


def get_account_center_keyboard(
    has_emby_account: bool,
) -> InlineKeyboardMarkup:
    """账号中心键盘

    功能说明:
    - 若已有 Emby 账号: 展示账号信息、线路信息、设备管理、修改密码, 每行两个, 底部返回主面板
    - 若尚无 Emby 账号: 展示开始注册与返回主面板, 每行一个

    输入参数:
    - has_emby_account: 是否已有 Emby 账号

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    builder = InlineKeyboardBuilder()
    if has_emby_account:
        builder.row(
            InlineKeyboardButton(text=USER_INFO_LABEL, callback_data="user:info"),
            InlineKeyboardButton(text=USER_LINES_LABEL, callback_data="user:lines"),
        )
        builder.row(
            InlineKeyboardButton(text=USER_DEVICES_LABEL, callback_data="user:devices"),
            InlineKeyboardButton(text=USER_PASSWORD_LABEL, callback_data="user:password"),
        )
        builder.row(InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back"))
    else:
        builder.row(InlineKeyboardButton(text=START_REGISTER_LABEL, callback_data="user:register"))
        builder.row(InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back"))
    return builder.as_markup()

