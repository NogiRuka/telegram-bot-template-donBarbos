from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizCategoryModel
from bot.keyboards.inline.admin import (
    get_quiz_category_cancel_keyboard,
    get_quiz_category_item_keyboard,
    get_quiz_category_list_keyboard,
)
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.admin import QuizAdminState
from bot.utils.message import send_toast
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2
from bot.utils.datetime import now


async def render_category_list(session: AsyncSession, main_msg: MainMessageService, user_id: int) -> None:
    """渲染分类列表"""
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.is_deleted == False).order_by(QuizCategoryModel.sort_order.asc(), QuizCategoryModel.id.asc())
    categories = (await session.execute(stmt)).scalars().all()

    text = "*🏷️ 分类管理*\n\n点击分类进行编辑或管理。"
    await main_msg.render(user_id, text, get_quiz_category_list_keyboard(categories))

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":category")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_categories(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示分类列表"""
    await render_category_list(session, main_msg, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":cat:add")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def add_category_start(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始添加分类"""
    text = "*➕ 添加分类*\n\n请输入新分类的名称："
    await main_msg.update_on_callback(callback, text, get_quiz_category_cancel_keyboard())
    await state.set_state(QuizAdminState.waiting_for_new_category_name)
    await callback.answer()

@router.message(QuizAdminState.waiting_for_new_category_name)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def add_category_process(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理添加分类"""
    await main_msg.delete_input(message)
    name = message.text.strip()
    if not name:
        await send_toast(message, "⚠️ 名称不能为空")
        return

    # Check exists
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.name == name)
    exists = (await session.execute(stmt)).scalar_one_or_none()
    if exists:
        await send_toast(message, "⚠️ 分类名称已存在")
        return

    # Get max order
    stmt = select(QuizCategoryModel.sort_order).order_by(QuizCategoryModel.sort_order.desc()).limit(1)
    max_order = (await session.execute(stmt)).scalar_one_or_none() or 0

    cat = QuizCategoryModel(name=name, sort_order=max_order + 1, is_active=True, created_by=message.from_user.id)
    session.add(cat)
    await session.commit()

    await state.clear()
    await send_toast(message, f"✅ 已添加分类：{name}")

    await render_category_list(session, main_msg, message.from_user.id)

@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":cat:view:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def view_category(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """查看分类详情"""
    cat_id = int(callback.data.split(":")[-1])
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == cat_id, QuizCategoryModel.is_deleted == False)
    cat = (await session.execute(stmt)).scalar_one_or_none()

    if not cat:
        await callback.answer("⚠️ 分类不存在", show_alert=True)
        await list_categories(callback, session, main_msg)
        return

    status = "🟢 启用" if cat.is_active else "🔴 禁用"
    text = (
        f"*🏷️ 分类详情*\n\n"
        f"ID: `{cat.id}`\n"
        f"名称: {escape_markdown_v2(cat.name)}\n"
        f"排序: {cat.sort_order}\n"
        f"状态: {status}"
    )
    await main_msg.update_on_callback(callback, text, get_quiz_category_item_keyboard(cat.id, cat.is_active))

@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":cat:edit:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def edit_category_start(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始编辑分类名称"""
    cat_id = int(callback.data.split(":")[-1])
    await state.update_data(cat_id=cat_id)

    text = "*✏️ 修改分类名称*\n\n请输入新的名称："
    await main_msg.update_on_callback(callback, text, get_quiz_category_cancel_keyboard())
    await state.set_state(QuizAdminState.waiting_for_category_name)
    await callback.answer()

@router.message(QuizAdminState.waiting_for_category_name)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def edit_category_process(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理编辑分类名称"""
    await main_msg.delete_input(message)
    name = message.text.strip()
    if not name:
        await send_toast(message, "⚠️ 名称不能为空")
        return

    data = await state.get_data()
    cat_id = data.get("cat_id")

    stmt = select(QuizCategoryModel).where(QuizCategoryModel.name == name)
    exists = (await session.execute(stmt)).scalar_one_or_none()
    if exists and exists.id != cat_id:
        await send_toast(message, "⚠️ 分类名称已存在")
        return

    stmt = update(QuizCategoryModel).where(QuizCategoryModel.id == cat_id).values(name=name, updated_by=message.from_user.id)
    await session.execute(stmt)
    await session.commit()

    await state.clear()
    await send_toast(message, f"✅ 已更新分类名称为：{name}")

    # Show detail view
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == cat_id)
    cat = (await session.execute(stmt)).scalar_one_or_none()
    if cat:
        status = "🟢 启用" if cat.is_active else "🔴 禁用"
        text = (
            f"*🏷️ 分类详情*\n\n"
            f"ID: `{cat.id}`\n"
            f"名称: {escape_markdown_v2(cat.name)}\n"
            f"排序: {cat.sort_order}\n"
            f"状态: {status}"
        )
        await main_msg.render(message.from_user.id, text, get_quiz_category_item_keyboard(cat.id, cat.is_active))
    else:
        await render_category_list(session, main_msg, message.from_user.id)

@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":cat:toggle:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def toggle_category(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """切换分类状态"""
    cat_id = int(callback.data.split(":")[-1])
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == cat_id, QuizCategoryModel.is_deleted == False)
    cat = (await session.execute(stmt)).scalar_one_or_none()

    if cat:
        cat.is_active = not cat.is_active
        cat.updated_by = callback.from_user.id
        await session.commit()
        await callback.answer("✅ 状态已更新")

        status = "🟢 启用" if cat.is_active else "🔴 禁用"
        text = (
            f"*🏷️ 分类详情*\n\n"
            f"ID: `{cat.id}`\n"
            f"名称: {escape_markdown_v2(cat.name)}\n"
            f"排序: {cat.sort_order}\n"
            f"状态: {status}"
        )
        await main_msg.update_on_callback(callback, text, get_quiz_category_item_keyboard(cat.id, cat.is_active))
    else:
        await callback.answer("⚠️ 分类不存在", show_alert=True)

@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":cat:delete:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def delete_category(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """删除分类"""
    cat_id = int(callback.data.split(":")[-1])

    stmt = update(QuizCategoryModel).where(QuizCategoryModel.id == cat_id).values(
        is_deleted=True,
        deleted_at=now(),
        deleted_by=callback.from_user.id,
        remark="分类删除"
    )
    await session.execute(stmt)
    await session.commit()

    await callback.answer("✅ 分类已删除")
    await render_category_list(session, main_msg, callback.from_user.id)
