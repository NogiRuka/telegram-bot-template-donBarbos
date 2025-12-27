import re
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import UserExtendModel, EmbyUserModel
from bot.keyboards.inline.user import get_user_tags_keyboard, get_tags_edit_keyboard
from bot.keyboards.inline.constants import (
    TAGS_CUSTOM_CALLBACK_DATA,
    TAGS_CLEAR_CALLBACK_DATA,
    TAGS_CANCEL_EDIT_CALLBACK_DATA,
    USER_TAGS_CALLBACK_DATA,
    USER_TAGS_LABEL,
)
from bot.services.main_message import MainMessageService
from bot.services.emby_service import update_user_blocked_tags
from bot.utils.permissions import require_user_feature

router = Router(name="user_tags")


class TagsStates(StatesGroup):
    """标签管理状态"""
    waiting_for_tags = State()


async def get_emby_user_model(session: AsyncSession, user_id: int) -> EmbyUserModel | None:
    """获取用户关联的 Emby 用户模型"""
    stmt = select(EmbyUserModel).join(
        UserExtendModel, 
        UserExtendModel.emby_user_id == EmbyUserModel.emby_user_id
    ).where(UserExtendModel.user_id == user_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def show_tags_menu(
    session: AsyncSession,
    main_msg: MainMessageService,
    uid: int,
    callback: CallbackQuery | None = None
) -> None:
    """显示标签管理菜单（公共逻辑）"""
    emby_user = await get_emby_user_model(session, uid)
    if not emby_user:
        msg = "❌ 未找到绑定的 Emby 账号"
        if callback:
            await callback.answer(msg)
        else:
            await main_msg.update(uid, msg)
        return

    policy = (emby_user.user_dto or {}).get("Policy", {})
    blocked_tags = policy.get("BlockedTags", [])
    
    if not blocked_tags:
        tags_display = "(无)"
    else:
        tags_display = ", ".join(blocked_tags)

    text = (
        f"{USER_TAGS_LABEL}\n\n"
        "您可以通过设置屏蔽标签来隐藏不想看到的内容。\n"
        "例如屏蔽 'AV' 标签可以隐藏相关成人内容。\n\n"
        f"📋 <b>当前屏蔽标签:</b>\n{tags_display}"
    )

    kb = get_user_tags_keyboard()

    if callback:
        await main_msg.update_on_callback(callback, text, kb)
        await callback.answer()
    else:
        await main_msg.update(uid, text, kb)


@router.callback_query(F.data == USER_TAGS_CALLBACK_DATA)
@require_user_feature("user.tags")
async def user_tags(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """处理标签屏蔽页面"""
    await show_tags_menu(session, main_msg, callback.from_user.id, callback)


@router.callback_query(F.data == TAGS_CLEAR_CALLBACK_DATA)
async def clear_tags(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """清除所有屏蔽标签"""
    uid = callback.from_user.id
    emby_user = await get_emby_user_model(session, uid)
    if not emby_user:
        await callback.answer("❌ 未找到绑定的 Emby 账号", show_alert=True)
        return

    success, err = await update_user_blocked_tags(session, emby_user.emby_user_id, [])
    if success:
        await callback.answer("✅ 已清除所有屏蔽标签")
        # 刷新页面
        await show_tags_menu(session, main_msg, uid, callback)
    else:
        await callback.answer(f"❌ 操作失败: {err}", show_alert=True)


@router.callback_query(F.data == TAGS_CUSTOM_CALLBACK_DATA)
async def start_custom_tags(
    callback: CallbackQuery,
    state: FSMContext,
    main_msg: MainMessageService,
) -> None:
    """开始自定义屏蔽标签"""
    text = (
        "✏️ <b>输入屏蔽标签</b>\n\n"
        "请输入您想要屏蔽的标签，多个标签请用<b>逗号</b>或<b>换行</b>分隔。\n"
        "例如: <code>AV, 恐怖, 惊悚</code>\n\n"
        "⚠️ 注意: 这将<b>覆盖</b>当前的屏蔽设置。"
    )
    kb = get_tags_edit_keyboard()
    
    await main_msg.update_on_callback(callback, text, kb)
    await state.set_state(TagsStates.waiting_for_tags)
    await callback.answer()


@router.callback_query(F.data == TAGS_CANCEL_EDIT_CALLBACK_DATA)
async def cancel_edit_tags(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    main_msg: MainMessageService,
) -> None:
    """取消编辑"""
    await state.clear()
    await show_tags_menu(session, main_msg, callback.from_user.id, callback)


@router.message(TagsStates.waiting_for_tags)
async def process_custom_tags(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    main_msg: MainMessageService,
) -> None:
    """处理用户输入的标签"""
    uid = message.from_user.id
    
    # 删除用户输入
    await main_msg.delete_input(message)
    
    text = (message.text or "").strip()
    if not text:
        return

    emby_user = await get_emby_user_model(session, uid)
    if not emby_user:
        await state.clear()
        await main_msg.update(uid, "❌ 未找到绑定的 Emby 账号")
        return

    # 解析标签：支持中英文逗号、换行分隔，保留标签内的空格
    tags = [t.strip() for t in re.split(r'[,，\n]+', text) if t.strip()]
    
    success, err = await update_user_blocked_tags(session, emby_user.emby_user_id, tags)
    
    await state.clear()
    
    if success:
        # 刷新页面并提示
        await show_tags_menu(session, main_msg, uid)
    else:
        await main_msg.update(uid, f"❌ 操作失败: {err}", get_user_tags_keyboard())
