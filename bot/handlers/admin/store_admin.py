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
        kb.as_markup()
    )


def _get_product_view(product):
    text = (
        f"📦 *商品管理 \- {escape_markdown_v2(product.name)}*\n\n"
        f"ID: `{product.id}`\n"
        f"名称: {escape_markdown_v2(product.name)}\n"
        f"价格: {product.price} {escape_markdown_v2(CURRENCY_SYMBOL)}\n"
        f"库存: {'无限' if product.stock == -1 else product.stock}\n"
        f"状态: {'🟢 上架中' if product.is_active else '🔴 已下架'}\n"
        f"描述: {escape_markdown_v2(product.description or '无')}\n"
        f"类型: {escape_markdown_v2(product.category)} / {escape_markdown_v2(product.action_type)}"
    )
    
    kb = InlineKeyboardBuilder()
    toggle_text = "🚫 下架" if product.is_active else "✅ 上架"
    kb.button(text=toggle_text, callback_data=f"{STORE_ADMIN_TOGGLE_PREFIX}{product.id}")
    kb.button(text="✏️ 价格", callback_data=f"{STORE_ADMIN_EDIT_PREFIX}price:{product.id}")
    kb.button(text="✏️ 库存", callback_data=f"{STORE_ADMIN_EDIT_PREFIX}stock:{product.id}")
    kb.button(text="✏️ 描述", callback_data=f"{STORE_ADMIN_EDIT_PREFIX}desc:{product.id}")
    kb.adjust(1, 3, 2)
    kb.row(BACK_TO_STORE_ADMIN_BUTTON, BACK_TO_HOME_BUTTON)
    return text, kb.as_markup()

async def _refresh_product_view(user_id: int, product_id: int, session: AsyncSession, main_msg: MainMessageService):
    product = await CurrencyService.get_product(session, product_id)
    if product:
        text, markup = _get_product_view(product)
        await main_msg.render(user_id, text, markup)

@router.callback_query(F.data.startswith(STORE_ADMIN_PRODUCT_PREFIX))
async def handle_product_detail(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """商品详情与管理"""
    try:
        product_id = extract_id(callback.data)
    except ValueError:
        await callback.answer("⚠️ 参数错误")
        return

    product = await CurrencyService.get_product(session, product_id)
    
    if not product:
        await callback.answer("⚠️ 商品不存在")
        return

    text, markup = _get_product_view(product)
    
    await main_msg.update_on_callback(callback, text, markup)

@router.callback_query(F.data.startswith(STORE_ADMIN_TOGGLE_PREFIX))
async def handle_toggle_active(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """切换上下架状态"""
    try:
        product_id = extract_id(callback.data)
    except ValueError:
        await callback.answer("⚠️ 参数错误")
        return

    product = await CurrencyService.get_product(session, product_id)
    
    if product:
        await CurrencyService.update_product(session, product_id, is_active=not product.is_active)
        # 刷新详情页
        product = await CurrencyService.get_product(session, product_id) # reload
        text, markup = _get_product_view(product)
        await main_msg.update_on_callback(callback, text, markup)
    else:
        await callback.answer("⚠️ 商品不存在")

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
async def process_price_update(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService):
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
    
    await _refresh_product_view(message.from_user.id, product_id, session, main_msg)

@router.message(StoreAdminState.waiting_for_stock)
async def process_stock_update(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService):
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
    
    await _refresh_product_view(message.from_user.id, product_id, session, main_msg)

@router.message(StoreAdminState.waiting_for_description)
async def process_desc_update(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService):
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
    
    await _refresh_product_view(message.from_user.id, product_id, session, main_msg)
