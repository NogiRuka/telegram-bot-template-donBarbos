from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class FeaturesPanelKeyboard:
    @staticmethod
    def main() -> InlineKeyboardMarkup:
        """功能开关面板键盘

        功能说明:
        - 提供总功能开关与示例子功能开关

        输入参数:
        - 无

        返回值:
        - InlineKeyboardMarkup: 功能开关键盘
        """
        btn_toggle_all = InlineKeyboardButton(
            text="🧲 切换全部功能",
            callback_data="features:toggle:all",
        )
        btn_toggle_emby = InlineKeyboardButton(
            text="🎬 切换 Emby 注册",
            callback_data="features:toggle:emby_register",
        )
        btn_toggle_admin_open = InlineKeyboardButton(
            text="🛂 切换管理员开放注册权限",
            callback_data="features:toggle:admin_open_registration",
        )
        btn_toggle_export = InlineKeyboardButton(
            text="📤 切换导出用户",
            callback_data="features:toggle:export_users",
        )
        btn_back = InlineKeyboardButton(
            text="↩️ 返回",
            callback_data="panel:main",
        )
        buttons = [
            [btn_toggle_all],
            [btn_toggle_emby],
            [btn_toggle_admin_open],
            [btn_toggle_export],
            [btn_back],
        ]
        kb = InlineKeyboardBuilder(markup=buttons)
        kb.adjust(1)
        return kb.as_markup()

