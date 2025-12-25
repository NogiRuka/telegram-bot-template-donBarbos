from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.database.database import sessionmaker
from bot.keyboards.inline.constants import (
    ESSENCE_STORE_CALLBACK_DATA,
    STORE_PRODUCT_PREFIX,
    STORE_BUY_PREFIX,
    CURRENCY_SYMBOL,
)
from bot.keyboards.inline.store import get_store_keyboard, get_product_detail_keyboard
from bot.services.currency import CurrencyService

router = Router(name="user_store")


@router.callback_query(F.data == ESSENCE_STORE_CALLBACK_DATA)
async def handle_store_list(callback: CallbackQuery):
    """处理商店列表展示"""
    user_id = callback.from_user.id
    
    async with sessionmaker() as session:
        # 获取用户余额
        balance = await CurrencyService.get_user_balance(session, user_id)
        # 获取商品列表
        products = await CurrencyService.get_products(session)
        
    text = (
        f"🛍️ **精粹商店**\n\n"
        f"当前余额: {balance} {CURRENCY_SYMBOL}\n\n"
        f"请选择要购买的商品:"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_store_keyboard(products),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith(STORE_PRODUCT_PREFIX))
async def handle_product_detail(callback: CallbackQuery):
    """处理商品详情展示"""
    product_id = int(callback.data.replace(STORE_PRODUCT_PREFIX, ""))
    user_id = callback.from_user.id
    
    async with sessionmaker() as session:
        product = await CurrencyService.get_product(session, product_id)
        balance = await CurrencyService.get_user_balance(session, user_id)
        
    if not product:
        await callback.answer("商品不存在", show_alert=True)
        return
        
    text = (
        f"📦 **商品详情**\n\n"
        f"名称: {product.name}\n"
        f"价格: {product.price} {CURRENCY_SYMBOL}\n"
        f"库存: {'无限' if product.stock == -1 else product.stock}\n\n"
        f"描述: {product.description or '暂无描述'}\n\n"
        f"当前余额: {balance} {CURRENCY_SYMBOL}"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_product_detail_keyboard(product),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith(STORE_BUY_PREFIX))
async def handle_product_purchase(callback: CallbackQuery):
    """处理购买请求"""
    product_id = int(callback.data.replace(STORE_BUY_PREFIX, ""))
    user_id = callback.from_user.id
    
    async with sessionmaker() as session:
        success, message = await CurrencyService.purchase_product(session, user_id, product_id)
        
        # 如果购买成功，刷新页面显示最新余额
        if success:
             # 获取最新余额
            balance = await CurrencyService.get_user_balance(session, user_id)
            # 重新获取商品信息（可能库存变化）
            product = await CurrencyService.get_product(session, product_id)
            
            if product:
                text = (
                    f"📦 **商品详情**\n\n"
                    f"名称: {product.name}\n"
                    f"价格: {product.price} {CURRENCY_SYMBOL}\n"
                    f"库存: {'无限' if product.stock == -1 else product.stock}\n\n"
                    f"描述: {product.description or '暂无描述'}\n\n"
                    f"当前余额: {balance} {CURRENCY_SYMBOL}\n\n"
                    f"✅ {message}"
                )
                await callback.message.edit_text(
                    text=text,
                    reply_markup=get_product_detail_keyboard(product),
                    parse_mode="Markdown"
                )
        
    await callback.answer(message, show_alert=True)
