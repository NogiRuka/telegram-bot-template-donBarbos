import base64
import io

from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.buttons import BACK_TO_ACCOUNT_BUTTON
from bot.keyboards.inline.constants import USER_AVATAR_CALLBACK_DATA, ACCOUNT_CENTER_LABEL
from bot.keyboards.inline.user import get_account_center_keyboard
from bot.services.main_message import MainMessageService
from bot.services.users import get_user_and_extend, has_emby_account
from bot.utils.emby import get_emby_client
from bot.utils.message import delete_message_after_delay
from bot.utils.permissions import require_emby_account, require_user_feature

router = Router(name="user_avatar")


class AvatarStates(StatesGroup):
    waiting_for_photo = State()


@router.callback_query(F.data == USER_AVATAR_CALLBACK_DATA)
@require_user_feature("user.avatar")
@require_emby_account
async def user_avatar(
    callback: CallbackQuery, 
    session: AsyncSession, 
    state: FSMContext, 
    main_msg: MainMessageService
) -> None:
    """进入修改头像流程"""
    uid = callback.from_user.id if callback.from_user else None
    if not uid:
        await callback.answer("🔴 无法获取用户ID", show_alert=True)
        return
        
    _user, ext = await get_user_and_extend(session, uid)
    
    caption = (
        "🖼️ *修改 Emby 头像*\n\n"
        "请直接发送一张图片作为新的头像。\n"
        "提示：建议使用正方形图片，支持 JPG/PNG 格式。"
    )
    
    kb = InlineKeyboardBuilder()
    kb.row(BACK_TO_ACCOUNT_BUTTON)
    
    await main_msg.update_on_callback(callback, caption, kb.as_markup())
    
    await state.set_state(AvatarStates.waiting_for_photo)
    await state.update_data(emby_user_id=ext.emby_user_id)
    await callback.answer()


@router.message(AvatarStates.waiting_for_photo, F.photo)
async def handle_avatar_photo(
    message: Message, 
    state: FSMContext, 
    main_msg: MainMessageService, 
    bot: Bot, 
    session: AsyncSession
) -> None:
    """处理用户发送的头像图片"""
    data = await state.get_data()
    emby_user_id = data.get("emby_user_id")
    
    if not emby_user_id:
        await message.answer("🔴 状态异常，请重新开始")
        await state.clear()
        return

    # 获取最大尺寸的图片
    if not message.photo:
        return
        
    photo = message.photo[-1]
    file_id = photo.file_id
    
    try:
        # 下载图片
        file_io = io.BytesIO()
        await bot.download(file_id, destination=file_io)
        file_content = file_io.getvalue()
        
        # 转 Base64
        b64_data = base64.b64encode(file_content).decode("utf-8")
        
        # 上传到 Emby
        client = get_emby_client()
        if not client:
            await message.answer("🔴 Emby 连接未配置")
            return
            
        await client.upload_user_image(emby_user_id, b64_data)
        
        # 成功提示
        success_msg = await message.answer("✅ 头像修改成功！")
        delete_message_after_delay(success_msg, 5)
        
        # 清理状态
        await state.clear()
        await main_msg.delete_input(message)
        
        # 刷新账号中心界面
        if message.from_user:
            user_has_emby = await has_emby_account(session, message.from_user.id)
            kb = get_account_center_keyboard(user_has_emby)
            await main_msg.render(message.from_user.id, f"*{ACCOUNT_CENTER_LABEL}*", kb)
        
    except Exception as e:
        logger.error(f"❌ 修改头像失败: {e}")
        err_msg = await message.answer("🔴 修改失败，请稍后重试")
        delete_message_after_delay(err_msg, 5)
        # 保持状态，允许用户重试


@router.message(AvatarStates.waiting_for_photo)
async def handle_invalid_content(message: Message, main_msg: MainMessageService) -> None:
    """处理非图片消息"""
    msg = await message.answer("⚠️ 请发送一张图片")
    delete_message_after_delay(msg, 3)
    await main_msg.delete_input(message)
