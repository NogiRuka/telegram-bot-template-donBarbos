import contextlib
import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_SYMBOL
from bot.database.models import UserModel
from bot.keyboards.inline.buttons import (
    BACK_TO_ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
    BACK_TO_STORE_ADMIN_BUTTON,
    STORE_ADMIN_ADD_PRODUCT_BUTTON,
    STORE_ADMIN_HISTORY_BUTTON,
)
from bot.keyboards.inline.constants import (
    STORE_ADMIN_ADD_PRODUCT_CALLBACK_DATA,
    STORE_ADMIN_CALLBACK_DATA,
    STORE_ADMIN_EDIT_PREFIX,
    STORE_ADMIN_HISTORY_CALLBACK_DATA,
    STORE_ADMIN_HISTORY_LABEL,
    STORE_ADMIN_LABEL,
    STORE_ADMIN_PRODUCT_PREFIX,
    STORE_ADMIN_TOGGLE_PREFIX,
)
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.states.admin import StoreAddProductState, StoreAdminState
from bot.utils.message import extract_id, send_toast
from bot.utils.text import build_user_link_html, escape_markdown_v2

router = Router(name="store_admin")

@router.callback_query(F.data == STORE_ADMIN_CALLBACK_DATA)
async def handle_store_admin_list(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """商店管理 - 商品列表"""
    # 清理可能存在的状态
    await state.clear()
    products = await CurrencyService.get_products(session, only_active=False)

    kb = InlineKeyboardBuilder()
    for product in products:
        status = "🟢" if product.is_active else "🔴"
        kb.button(
            text=f"{status} {product.name} ({product.price} {CURRENCY_SYMBOL})",
            callback_data=f"{STORE_ADMIN_PRODUCT_PREFIX}{product.id}"
        )

    kb.adjust(1)
    kb.row(STORE_ADMIN_ADD_PRODUCT_BUTTON, STORE_ADMIN_HISTORY_BUTTON)
    kb.row(BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON)
    text = (f"*{STORE_ADMIN_LABEL}*\n\n请选择要管理的商品 （🟢上架中 / 🔴已下架）")

    await main_msg.update_on_callback(
        callback,
        text,
        kb.as_markup()
    )


def _get_product_view(product):
    text = (
        f"📦 *商品管理 \\- {escape_markdown_v2(product.name)}*\n\n"
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

async def _refresh_product_view(user_id: int, product_id: int, session: AsyncSession, main_msg: MainMessageService) -> None:
    product = await CurrencyService.get_product(session, product_id)
    if product:
        text, markup = _get_product_view(product)
        await main_msg.render(user_id, text, markup)

@router.callback_query(F.data.startswith(STORE_ADMIN_PRODUCT_PREFIX))
async def handle_product_detail(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """商品详情与管理"""
    await state.clear()
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
async def handle_toggle_active(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """切换上下架状态"""
    await state.clear()
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
async def handle_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    """开始修改信息"""
    await callback.answer()
    await state.clear()
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
async def process_price_update(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

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

@router.callback_query(F.data == STORE_ADMIN_HISTORY_CALLBACK_DATA)
async def handle_purchase_history(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """查看购买记录"""
    await state.clear()
    # 仅显示最近 20 条
    history = await CurrencyService.get_purchase_history(session, limit=20)

    if not history:
        text = f"<b>{html.escape(STORE_ADMIN_HISTORY_LABEL)}</b>\n\n暂无购买记录。"
    else:
        user_ids = sorted({int(tx.user_id) for tx in history})
        user_name_map: dict[int, tuple[str | None, str | None]] = {}
        if user_ids:
            stmt = select(UserModel.id, UserModel.first_name, UserModel.last_name).where(UserModel.id.in_(user_ids))
            rows = (await session.execute(stmt)).all()
            user_name_map = {int(uid): (first_name, last_name) for uid, first_name, last_name in rows}

        lines = []
        for tx in history:
            first_name, last_name = user_name_map.get(int(tx.user_id), ("Unknown", None))
            user_link = build_user_link_html(tx.user_id, first_name, last_name)
            date_str = tx.created_at.strftime("%Y-%m-%d %H:%M")
            product_name = tx.meta.get("product_name", "未知商品") if tx.meta else "未知商品"
            lines.append(
                f"• <code>{html.escape(date_str)}</code> {user_link} 购买了 <b>{html.escape(product_name)}</b> "
                f"({html.escape(str(tx.amount))} {html.escape(CURRENCY_SYMBOL)})"
            )

        text = f"<b>{html.escape(STORE_ADMIN_HISTORY_LABEL)} (最近20条)</b>\n\n" + "\n".join(lines)

    kb = InlineKeyboardBuilder()
    kb.row(BACK_TO_STORE_ADMIN_BUTTON, BACK_TO_HOME_BUTTON)

    await main_msg.update_on_callback(callback, text, kb.as_markup(), parse_mode="HTML")


# ===== 添加商品流程 =====

@router.callback_query(F.data == STORE_ADMIN_ADD_PRODUCT_CALLBACK_DATA)
async def handle_add_product_start(callback: CallbackQuery, state: FSMContext) -> None:
    """开始添加商品"""
    await callback.answer()
    await state.clear()
    await send_toast(callback, "📦 请输入商品名称:")
    await state.set_state(StoreAddProductState.waiting_for_name)


@router.message(StoreAddProductState.waiting_for_name)
async def process_add_name(message: Message, state: FSMContext) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

    name = message.text.strip()
    if not name:
        await send_toast(message, "❌ 名称不能为空")
        return

    await state.update_data(name=name)
    await send_toast(message, "💰 请输入商品价格 (整数):")
    await state.set_state(StoreAddProductState.waiting_for_price)


@router.message(StoreAddProductState.waiting_for_price)
async def process_add_price(message: Message, state: FSMContext) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

    try:
        price = int(message.text)
        if price < 0:
            raise ValueError
    except ValueError:
        await send_toast(message, "❌ 请输入有效的非负整数")
        return

    await state.update_data(price=price)
    await send_toast(message, "📦 请输入商品库存 (-1 为无限):")
    await state.set_state(StoreAddProductState.waiting_for_stock)


@router.message(StoreAddProductState.waiting_for_stock)
async def process_add_stock(message: Message, state: FSMContext) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

    try:
        stock = int(message.text)
    except ValueError:
        await send_toast(message, "❌ 请输入有效的整数")
        return

    await state.update_data(stock=stock)
    await send_toast(message, "📝 请输入商品描述:")
    await state.set_state(StoreAddProductState.waiting_for_description)


@router.message(StoreAddProductState.waiting_for_description)
async def process_add_desc(message: Message, state: FSMContext) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

    desc = message.text.strip()
    await state.update_data(description=desc)

    # 这里为了简化，直接要求输入分类，也可以做成按钮选择
    await send_toast(message, "📂 请输入商品分类 (如: 会员, 道具):")
    await state.set_state(StoreAddProductState.waiting_for_category)


@router.message(StoreAddProductState.waiting_for_category)
async def process_add_category(message: Message, state: FSMContext) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

    category = message.text.strip()
    if not category:
        category = "其他"

    await state.update_data(category=category)
    await send_toast(message, "⚡ 请输入动作类型 (如: none, retro_checkin):")
    await state.set_state(StoreAddProductState.waiting_for_action_type)


@router.message(StoreAddProductState.waiting_for_action_type)
async def process_add_action_type(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

    action_type = message.text.strip()
    if not action_type:
        action_type = "none"

    data = await state.get_data()

    # 创建商品
    product = await CurrencyService.create_product(
        session=session,
        name=data["name"],
        price=data["price"],
        stock=data["stock"],
        description=data["description"],
        category=data["category"],
        action_type=action_type,
        is_active=False  # 默认下架
    )

    await send_toast(message, f"✅ 商品 '{product.name}' 创建成功！(默认已下架)")
    await state.clear()

    # 刷新并显示新商品详情
    await _refresh_product_view(message.from_user.id, product.id, session, main_msg)


@router.message(StoreAdminState.waiting_for_stock)
async def process_stock_update(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

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
async def process_desc_update(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    with contextlib.suppress(Exception):
        await message.delete()

    desc = message.text

    data = await state.get_data()
    product_id = data["product_id"]

    await CurrencyService.update_product(session, product_id, description=desc)
    await send_toast(message, "✅ 描述已更新")
    await state.clear()

    await _refresh_product_view(message.from_user.id, product_id, session, main_msg)
