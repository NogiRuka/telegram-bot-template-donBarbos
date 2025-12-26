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
from bot.keyboards.inline.buttons import BACK_TO_ADMIN_PANEL_BUTTON
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.states.admin import StoreAdminState
from bot.database.models import CurrencyProductModel

router = Router(name="store_admin")

@router.callback_query(F.data == STORE_ADMIN_CALLBACK_DATA)
async def handle_store_admin_list(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """商店管理 - 商品列表"""
    products = await CurrencyService.get_products(session, only_active=False)
    
    kb = InlineKeyboardBuilder()
    for product in products:
        status = "🟢" if product.is_active else "🔴"
        kb.button(
            text=f"{status} {product.name} ({product.price})",
            callback_data=f"{STORE_ADMIN_PRODUCT_PREFIX}{product.id}"
        )
    
    kb.adjust(1)
    kb.row(BACK_TO_ADMIN_PANEL_BUTTON)
    
    await main_msg.update_on_callback(
        callback,
        "🏪 **商店管理**\n\n请选择要管理的商品 (🟢上架中 / 🔴已下架):",
        kb.as_markup()
    )

@router.callback_query(F.data.startswith(STORE_ADMIN_PRODUCT_PREFIX))
async def handle_product_detail(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """商品详情与管理"""
    product_id = int(callback.data.replace(STORE_ADMIN_PRODUCT_PREFIX, ""))
    product = await CurrencyService.get_product(session, product_id)
    
    if not product:
        await callback.answer("商品不存在", show_alert=True)
        return

    text = (
        f"📦 **商品管理 - {product.name}**\n\n"
        f"ID: `{product.id}`\n"
        f"名称: {product.name}\n"
        f"价格: {product.price} {CURRENCY_SYMBOL}\n"
        f"库存: {'无限' if product.stock == -1 else product.stock}\n"
        f"状态: {'🟢 上架中' if product.is_active else '🔴 已下架'}\n"
        f"描述: {product.description}\n"
        f"类型: {product.category} / {product.action_type}"
    )
    
    kb = InlineKeyboardBuilder()
    
    # 状态切换按钮
    toggle_text = "🚫 下架" if product.is_active else "✅ 上架"
    kb.button(text=toggle_text, callback_data=f"{STORE_ADMIN_TOGGLE_PREFIX}{product.id}")
    
    # 修改按钮
    kb.button(text="✏️ 修改价格", callback_data=f"{STORE_ADMIN_EDIT_PREFIX}price:{product.id}")
    kb.button(text="✏️ 修改库存", callback_data=f"{STORE_ADMIN_EDIT_PREFIX}stock:{product.id}")
    kb.button(text="✏️ 修改描述", callback_data=f"{STORE_ADMIN_EDIT_PREFIX}desc:{product.id}")
    
    kb.adjust(1, 2, 1)
    
    # 返回列表
    kb.row(InlineKeyboardButton(text="🔙 返回商品列表", callback_data=STORE_ADMIN_CALLBACK_DATA))
    
    await main_msg.update_on_callback(callback, text, kb.as_markup())

@router.callback_query(F.data.startswith(STORE_ADMIN_TOGGLE_PREFIX))
async def handle_toggle_active(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """切换上下架状态"""
    product_id = int(callback.data.replace(STORE_ADMIN_TOGGLE_PREFIX, ""))
    product = await CurrencyService.get_product(session, product_id)
    
    if product:
        await CurrencyService.update_product(session, product_id, is_active=not product.is_active)
        # 刷新详情页
        await handle_product_detail(callback, session, main_msg)
    else:
        await callback.answer("商品不存在", show_alert=True)

@router.callback_query(F.data.startswith(STORE_ADMIN_EDIT_PREFIX))
async def handle_edit_start(callback: CallbackQuery, state: FSMContext):
    """开始修改信息"""
    action, product_id = callback.data.replace(STORE_ADMIN_EDIT_PREFIX, "").split(":")
    product_id = int(product_id)
    
    await state.update_data(product_id=product_id)
    
    if action == "price":
        await callback.message.answer("请输入新的价格 (整数):")
        await state.set_state(StoreAdminState.waiting_for_price)
    elif action == "stock":
        await callback.message.answer("请输入新的库存 (-1 为无限):")
        await state.set_state(StoreAdminState.waiting_for_stock)
    elif action == "desc":
        await callback.message.answer("请输入新的描述:")
        await state.set_state(StoreAdminState.waiting_for_description)
    
    await callback.answer()

@router.message(StoreAdminState.waiting_for_price)
async def process_price_update(message: Message, state: FSMContext, session: AsyncSession):
    try:
        price = int(message.text)
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ 请输入有效的非负整数。")
        return
        
    data = await state.get_data()
    product_id = data["product_id"]
    
    await CurrencyService.update_product(session, product_id, price=price)
    await message.answer(f"✅ 价格已更新为 {price}")
    await state.clear()

@router.message(StoreAdminState.waiting_for_stock)
async def process_stock_update(message: Message, state: FSMContext, session: AsyncSession):
    try:
        stock = int(message.text)
    except ValueError:
        await message.answer("❌ 请输入有效的整数。")
        return
        
    data = await state.get_data()
    product_id = data["product_id"]
    
    await CurrencyService.update_product(session, product_id, stock=stock)
    await message.answer(f"✅ 库存已更新为 {stock}")
    await state.clear()

@router.message(StoreAdminState.waiting_for_description)
async def process_desc_update(message: Message, state: FSMContext, session: AsyncSession):
    desc = message.text
    
    data = await state.get_data()
    product_id = data["product_id"]
    
    await CurrencyService.update_product(session, product_id, description=desc)
    await message.answer(f"✅ 描述已更新。")
    await state.clear()
