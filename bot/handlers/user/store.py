from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_USER_STORE
from bot.core.constants import CURRENCY_NAME, CURRENCY_SYMBOL
from bot.keyboards.inline.constants import (
    ESSENCE_STORE_CALLBACK_DATA,
    STORE_PRODUCT_PREFIX,
    STORE_BUY_PREFIX,
    ESSENCE_STORE_LABEL,
)
from bot.keyboards.inline.store import get_store_keyboard, get_product_detail_keyboard
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_user_feature
from bot.utils.text import escape_markdown_v2

router = Router(name="user_store")


@router.callback_query(F.data == ESSENCE_STORE_CALLBACK_DATA)
@require_user_feature(KEY_USER_STORE)
async def handle_store_list(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """处理商店列表展示"""
    user_id = callback.from_user.id
    
    # 获取用户余额
    balance = await CurrencyService.get_user_balance(session, user_id)
    # 获取商品列表 (传入 user_id 用于过滤可见性)
    products = await CurrencyService.get_products(session, user_id=user_id)
        
    currency_name = CURRENCY_NAME
    text = (
        f"{ESSENCE_STORE_LABEL}\n\n" 
        f"当前{currency_name}: {balance} {CURRENCY_SYMBOL}\n\n"
        f"请选择要购买的商品:"
    )
    
    await main_msg.update_on_callback(
        callback,
        text,
        get_store_keyboard(products)
    )


@router.callback_query(F.data.startswith(STORE_PRODUCT_PREFIX))
@require_user_feature(KEY_USER_STORE)
async def handle_product_detail(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """处理商品详情展示"""
    product_id = int(callback.data.replace(STORE_PRODUCT_PREFIX, ""))
    
    product = await CurrencyService.get_product(session, product_id)
        
    if not product:
        await callback.answer("商品不存在", show_alert=True)
        return
        
    text = (
        f"📦 *商品详情*\n\n"
        f"名称：{escape_markdown_v2(product.name)}\n"
        f"价格：{product.price} {escape_markdown_v2(CURRENCY_SYMBOL)}\n"
        f"库存：{'无限' if product.stock == -1 else product.stock}\n\n"
        f"描述：{escape_markdown_v2(product.description or '暂无描述')}"
    )
    
    await main_msg.update_on_callback(
        callback,
        text,
        get_product_detail_keyboard(product)
    )


@router.callback_query(F.data.startswith(STORE_BUY_PREFIX))
@require_user_feature(KEY_USER_STORE)
async def handle_product_purchase(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """处理购买请求"""
    product_id = int(callback.data.replace(STORE_BUY_PREFIX, ""))
    user_id = callback.from_user.id
    
    success, message = await CurrencyService.purchase_product(session, user_id, product_id)
    
    # 如果购买成功，刷新页面显示最新余额
    if success:
         # 获取最新余额
        balance = await CurrencyService.get_user_balance(session, user_id)
        # 重新获取商品信息（可能库存变化）
        product = await CurrencyService.get_product(session, product_id)
        
        if product:
            text = (
                f"📦 *商品详情*\n\n"
                f"名称: {escape_markdown_v2(product.name)}\n"
                f"价格: {product.price} {escape_markdown_v2(CURRENCY_SYMBOL)}\n"
                f"库存: {'无限' if product.stock == -1 else product.stock}\n\n"
                f"描述: {escape_markdown_v2(product.description or '暂无描述')}\n\n"
                f"当前余额: {balance} {escape_markdown_v2(CURRENCY_SYMBOL)}\n\n"
                f"{escape_markdown_v2(message)}"
            )
            await main_msg.update_on_callback(
                callback,
                text,
                get_product_detail_keyboard(product)
            )
        else:
            await callback.answer(message, show_alert=True)
    else:
        await callback.answer(message, show_alert=True)
