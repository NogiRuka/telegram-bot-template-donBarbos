from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class OwnerPanelKeyboard:
    @staticmethod
    def main() -> InlineKeyboardMarkup:
        """所有者主面板键盘

        功能说明:
        - 提供总开关、功能开关与管理员管理入口

        输入参数:
        - 无

        返回值:
        - InlineKeyboardMarkup: 面板主键盘
        """
        buttons = [
            [InlineKeyboardButton(text="🚦 机器人总开关", callback_data="panel:toggle:bot")],
            [InlineKeyboardButton(text="🧩 功能开关", callback_data="panel:features")],
            [InlineKeyboardButton(text="👮 管理员管理", callback_data="panel:admins")],
            [InlineKeyboardButton(text="↩️ 返回主面板", callback_data="panel:back")],
        ]
        kb = InlineKeyboardBuilder(markup=buttons)
        kb.adjust(1)
        return kb.as_markup()

