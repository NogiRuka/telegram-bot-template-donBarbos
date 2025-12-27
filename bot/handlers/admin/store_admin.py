from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_SYMBOL
from bot.keyboards.inline.constants import (
    STORE_ADMIN_CALLBACK_DATA,
    STORE_ADMIN_PRODUCT_PREFIX,
    STORE_ADMIN_EDIT_PREFIX,
    STORE_ADMIN_TOGGLE_PREFIX,
)
from bot.keyboards.inline.buttons import BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON, BACK_TO_STORE_ADMIN_BUTTON
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.states.admin import StoreAdminState
from bot.utils.images import get_common_image
from bot.utils.message import send_toast, extract_id
from bot.utils.text import escape_markdown_v2
from loguru import logger


router = Router(name="store_admin")

@router.callback_query(F.data == STORE_ADMIN_CALLBACK_DATA)
async def handle_store_admin_list(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """商店管理 - 商品列表"""
    products = await CurrencyService.get_products(session, only_active=False)
    
    kb = InlineKeyboardBuilder()
    for product in products:
        status = "🟢" if product.is_active else "🔴"
        kb.button(
            text=f"{status} {product.name} ({product.price} {CURRENCY_SYMBOL})",
            callback_data=f"{STORE_ADMIN_PRODUCT_PREFIX}{product.id}"
        )
    
    kb.adjust(1)
    kb.row(BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON)
    text = ("🏪 商店管理\n\n请选择要管理的商品 (🟢上架中 / 🔴已下架):")
    
    await main_msg.update_on_callback(
        callback,
        text,
        kb.as_markup(),
        image_path=get_common_image()
    )



@router.callback_query(F.data.startswith(STORE_ADMIN_EDIT_PREFIX))
async def handle_edit_start(callback: CallbackQuery, state: FSMContext):
    """开始修改信息"""
    await callback.answer()
    parts = callback.data.split(":")
    action = parts[-2]
    product_id = int(parts[-1])
    
    await state.update_data(product_id=product_id)
    
    if action == "price":
        await send_toast(callback, "✏️ 请输入新的价格 (整数):")
        await state.set_state(StoreAdminState.waiting_for_price)
    elif action == "stock":
        await send_toast(callback, "📦 请输入新的库存 (-1 为无限):")
        await state.set_state(StoreAdminState.waiting_for_stock)
    elif action == "desc":
        await send_toast(callback, "📝 请输入新的描述:")
        await state.set_state(StoreAdminState.waiting_for_description)
    else:
        await callback.answer("⚠️ 未知操作")


@router.message(StoreAdminState.waiting_for_price)
async def process_price_update(message: Message, state: FSMContext, session: AsyncSession):
    try:
        await message.delete()
    except Exception:
        pass

    try:
        price = int(message.text)
        if price < 0:
            raise ValueError
    except ValueError:
        await send_toast(message, "❌ 请输入有效的非负整数。")
        return
        
    data = await state.get_data()
    product_id = data["product_id"]
    
    await CurrencyService.update_product(session, product_id, price=price)
    await send_toast(message, f"✅ 价格已更新为 {price} {CURRENCY_SYMBOL}")
    await state.clear()

@router.message(StoreAdminState.waiting_for_stock)
async def process_stock_update(message: Message, state: FSMContext, session: AsyncSession):
    try:
        await message.delete()
    except Exception:
        pass

    try:
        stock = int(message.text)
    except ValueError:
        await send_toast(message, "❌ 请输入有效的整数。")
        return
        
    data = await state.get_data()
    product_id = data["product_id"]
    
    await CurrencyService.update_product(session, product_id, stock=stock)
    await send_toast(message, f"✅ 库存已更新为 {stock}")
    await state.clear()

@router.message(StoreAdminState.waiting_for_description)
async def process_desc_update(message: Message, state: FSMContext, session: AsyncSession):
    try:
        await message.delete()
    except Exception:
        pass

    desc = message.text
    
    data = await state.get_data()
    product_id = data["product_id"]
    
    await CurrencyService.update_product(session, product_id, description=desc)
    await send_toast(message, "✅ 描述已更新")
    await state.clear()
n, main_msg: MaiMessageServicear()
    
    awit _refresh_poduct_viewmessage.from_user.id, product_id, session, main_msgn, main_msg: MaiMessageServicear()
    
    awit _refresh_poduct_viewmessage.from_user.id, product_id, session, main_msgn, main_msg: MaiMessageServicear()
    
    awit _refresh_poduct_viewmessage.from_user.id, product_id, session, main_msg