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
        buttons = [
            [InlineKeyboardButton(text="🧲 切换全部功能", callback_data="features:toggle:all")],
            [InlineKeyboardButton(text="📤 切换导出用户", callback_data="features:toggle:export_users")],
            [InlineKeyboardButton(text="↩️ 返回", callback_data="panel:main")],
        ]
        kb = InlineKeyboardBuilder(markup=buttons)
        kb.adjust(1)
        return kb.as_markup()

