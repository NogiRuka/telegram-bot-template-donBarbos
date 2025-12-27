from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserModel
from bot.core.constants import CURRENCY_SYMBOL
from bot.keyboards.inline.constants import (
    CURRENCY_ADMIN_CALLBACK_DATA,
)
from bot.services.currency import CurrencyService
from bot.states.admin import CurrencyAdminState
from bot.utils.message import send_temp_message, send_toast
from bot.utils.text import escape_markdown_v2

router = Router(name="currency_admin")

@router.callback_query(F.data == CURRENCY_ADMIN_CALLBACK_DATA)
async def handle_currency_admin_start(callback: CallbackQuery, state: FSMContext):
    """精粹管理 - 开始"""
    msg = await callback.message.answer("💎 精粹管理\n\n请发送用户的 ID (或者回复用户的消息) 来查询/管理余额:")
    await state.update_data(prompt_message_id=msg.message_id)
    await state.set_state(CurrencyAdminState.waiting_for_user)
    await callback.answer()


@router.message(CurrencyAdminState.waiting_for_user)
async def process_user_lookup(message: Message, state: FSMContext, session: AsyncSession):
    # 尝试删除用户发送的消息
    try:
        await message.delete()
    except Exception:
        pass

    # 尝试删除之前的提示消息
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    if prompt_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
        except Exception:
            pass

    user_id = None
    
    # 尝试从文本中解析 ID
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await send_toast(message, "❌ 无效的用户 ID，请输入数字 ID。")
        return
            
    # 检查用户是否存在
    user_result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        await send_toast(message, "❌ 找不到该用户。")
        return
        
    # 获取余额
    balance = await CurrencyService.get_user_balance(session, user_id)
    
    await state.update_data(target_user_id=user_id, current_balance=balance)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ 手动加/扣币", callback_data="admin:currency:modify")
    kb.button(text="❌ 取消", callback_data="admin:currency:cancel")
    kb.adjust(1)

    first_name = getattr(user, "first_name", "") or ""
    last_name = getattr(user, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip() or "未知"

    username = getattr(user, "username", None)
    username_display = f"@{username}" if username else "未设置"

    text = (
        f"👤 *用户查询结果*\n\n"
        f"ID: `{user.id}`\n"
        f"昵称: {escape_markdown_v2(full_name)}\n"
        f"用户名: {escape_markdown_v2(username_display)}\n"
        f"当前余额: {balance} {CURRENCY_SYMBOL}"
    )
    
    msg = await message.answer(text, reply_markup=kb.as_markup(), parse_mode="MarkdownV2")
    await state.update_data(prompt_message_id=msg.message_id)

@router.callback_query(F.data == "admin:currency:modify")
async def handle_modify_start(callback: CallbackQuery, state: FSMContext):
    """开始修改余额"""
    text = (
        "请输入要变动的数值 (整数):\n"
        "➕ 正数增加 (例如 100)\n"
        "➖ 负数扣除 (例如 -50)"
    )
    # 编辑当前消息
    await callback.message.edit_text(text=text)
    await state.set_state(CurrencyAdminState.waiting_for_amount)
    await callback.answer()

@router.callback_query(F.data == "admin:currency:cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text("已取消操作。")

@router.message(CurrencyAdminState.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    # 尝试删除用户发送的消息
    try:
        await message.delete()
    except Exception:
        pass

    try:
        amount = int(message.text)
        if amount == 0:
             await send_toast(message, "❌ 变动值不能为 0")
             return
    except ValueError:
        await send_toast(message, "❌ 请输入有效的整数。")
        return
        
    await state.update_data(amount=amount)
    
    # 获取 prompt_message_id 并编辑消息
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    
    text = "📝 请输入操作原因 (必填):"
    
    if prompt_message_id:
        try:
            await message.bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=prompt_message_id
            )
        except Exception:
            msg = await message.answer(text)
            await state.update_data(prompt_message_id=msg.message_id)
    else:
        msg = await message.answer(text)
        await state.update_data(prompt_message_id=msg.message_id)

    await state.set_state(CurrencyAdminState.waiting_for_reason)

@router.message(CurrencyAdminState.waiting_for_reason)
async def process_reason(message: Message, state: FSMContext, session: AsyncSession):
    # 删除用户发送的消息
    try:
        await message.delete()
    except Exception:
        pass
    
    reason = message.text.strip()
    if not reason:
        await send_toast(message, "❌ 原因不能为空。")
        return
        
    data = await state.get_data()
    user_id = data["target_user_id"]
    amount = data["amount"]
    prompt_message_id = data.get("prompt_message_id")

    try:
        new_balance = await CurrencyService.add_currency(
            session,
            user_id,
            amount,
            "admin_manual",
            f"管理员手动操作: {reason}",
            meta={"admin_id": message.from_user.id}
        )
        
        action = "增加" if amount > 0 else "扣除"
        text = (
            f"✅ *操作成功*\n\n"
            f"用户 ID: `{user_id}`\n"
            f"变动: {action} {abs(amount)} {CURRENCY_SYMBOL}\n"
            f"原因: {escape_markdown_v2(reason)}\n"
            f"最新余额: {new_balance} {CURRENCY_SYMBOL}"
        )
        
        if prompt_message_id:
            try:
                await message.bot.edit_message_text(
                    text=text,
                    chat_id=message.chat.id,
                    message_id=prompt_message_id,
                    parse_mode="MarkdownV2"
                )
                asyncio.create_task(delete_message_later(message.chat.id, prompt_message_id, message.bot))
            except Exception:
                msg = await message.answer(text, parse_mode="MarkdownV2")
                asyncio.create_task(delete_message_later(message.chat.id, msg.message_id, message.bot))
        else:
            msg = await message.answer(text, parse_mode="MarkdownV2")
            asyncio.create_task(delete_message_later(message.chat.id, msg.message_id, message.bot))

    except Exception as e:
        await send_toast(message, f"❌ 操作失败: {escape_markdown_v2(str(e))}", delay = 5)

    await state.clear()
