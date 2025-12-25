from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models.currency import CurrencyProductModel
from bot.keyboards.inline.constants import (
    STORE_PRODUCT_PREFIX,
    STORE_BUY_PREFIX,
    STORE_BACK_LABEL,
    STORE_BACK_CALLBACK_DATA,
    CURRENCY_SYMBOL,
)


def get_store_keyboard(products: list[CurrencyProductModel]) -> InlineKeyboardMarkup:
    """商店商品列表键盘
    
    功能说明:
    - 展示所有上架商品
    - 底部返回按钮
    
    输入参数:
    - products: 商品列表
    
    返回值:
    - InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    for product in products:
        # 按钮文本: 商品名 - 价格
        text = f"{product.name} ({product.price} {CURRENCY_SYMBOL})"
        callback_data = f"{STORE_PRODUCT_PREFIX}{product.id}"
        builder.button(text=text, callback_data=callback_data)
        
    builder.adjust(1)  # 每行一个商品
    
    # 底部返回按钮
    builder.row(
        InlineKeyboardButton(text=STORE_BACK_LABEL, callback_data=STORE_BACK_CALLBACK_DATA)
    )
    
    return builder.as_markup()


def get_product_detail_keyboard(product: CurrencyProductModel) -> InlineKeyboardMarkup:
    """商品详情键盘
    
    功能说明:
    - 购买按钮
    - 返回商店列表按钮
    
    输入参数:
    - product: 商品对象
    
    返回值:
    - InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    # 购买按钮
    buy_text = f"购买 (-{product.price} {CURRENCY_SYMBOL})"
    buy_callback = f"{STORE_BUY_PREFIX}{product.id}"
    builder.button(text=buy_text, callback_data=buy_callback)
    
    builder.adjust(1)
    
    # 返回按钮
    builder.row(
        InlineKeyboardButton(text="🔙 返回商店", callback_data=ESSENCE_STORE_CALLBACK_DATA)
    )
    
    return builder.as_markup()
