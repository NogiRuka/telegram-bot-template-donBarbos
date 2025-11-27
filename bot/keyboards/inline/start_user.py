from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
            InlineKeyboardButton(text="👤 个人信息", callback_data="user:profile"),
            InlineKeyboardButton(text="🧩 账号中心", callback_data="user:account"),
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
    features: dict[str, bool] | None = None,
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
            InlineKeyboardButton(text="👤 账号信息", callback_data="user:info"),
            InlineKeyboardButton(text="🛰️ 线路信息", callback_data="user:lines"),
        )
        builder.row(
            InlineKeyboardButton(text="📱 设备管理", callback_data="user:devices"),
            InlineKeyboardButton(text="🔐 修改密码", callback_data="user:password"),
        )
        builder.row(InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"))
    else:
        builder.row(InlineKeyboardButton(text="🎬 开始注册", callback_data="user:register"))
        builder.row(InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"))
    # 根据功能开关过滤显示
    if features:
        def enabled(k: str) -> bool:
            return bool(features.get(k, True))
        # 过滤行: 遍历已构建的行并移除禁用的按钮
        rows = []
        for row in builder.export():
            filtered = []
            for btn in row:
                data = getattr(btn, "callback_data", "")
                if data in {"home:back"}:
                    filtered.append(btn)
                    continue
                key = data.replace(":", ".") if data.startswith("user:") else data
                if key.startswith("user.") and enabled(key):
                    filtered.append(btn)
            if filtered:
                rows.append(filtered)
        builder = InlineKeyboardBuilder(markup=rows)
    return builder.as_markup()

