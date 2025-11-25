from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AdminsPanelKeyboard:
    @staticmethod
    def main() -> InlineKeyboardMarkup:
        """管理员管理面板键盘

        功能说明:
        - 提供查看与返回入口

        输入参数:
        - 无

        返回值:
        - InlineKeyboardMarkup: 管理员面板键盘
        """
        buttons = [
            [InlineKeyboardButton(text="👀 查看管理员列表", callback_data="admins:list")],
            [InlineKeyboardButton(text="↩️ 返回", callback_data="panel:main")],
        ]
        kb = InlineKeyboardBuilder(markup=buttons)
        kb.adjust(1)
        return kb.as_markup()

