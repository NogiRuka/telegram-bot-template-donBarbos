import contextlib
from math import ceil

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from .list_utils import _clear_quiz_list
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizQuestionModel
from bot.keyboards.inline.admin import (
    get_quiz_question_item_keyboard,
    get_quiz_question_list_pagination_keyboard,
)
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.datetime import now
from bot.utils.message import safe_delete_message, send_toast
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":list:view:question:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_questions_view(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """显示题目列表（分页）"""
    # 解析参数: admin:quiz:list:view:question:1:5
    try:
        parts = callback.data.split(":")
        page = int(parts[5])
        limit = int(parts[6])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    # 先清理旧消息
    if callback.message:
        await _clear_quiz_list(state, callback.bot, callback.message.chat.id)

    # 计算总数 (排除软删除)
    count_stmt = select(func.count()).where(QuizQuestionModel.is_deleted.is_(False))
    total_count = (await session.execute(count_stmt)).scalar_one()
    total_pages = ceil(total_count / limit) if total_count > 0 else 1

    # 如果页码超出范围则调整
    page = min(page, total_pages)
    page = max(page, 1)

    # 查询数据
    stmt = (
        select(QuizQuestionModel)
        .where(QuizQuestionModel.is_deleted.is_(False))
        .order_by(QuizQuestionModel.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = (await session.execute(stmt)).scalars().all()

    # 更新控制消息
    text = (
        f"*📋 题目列表*\n"
        f"共 {total_count} 条，当前第 {page}/{total_pages} 页"
    )
    await main_msg.update_on_callback(
        callback,
        text,
        get_quiz_question_list_pagination_keyboard(page, total_pages, limit)
    )

    # 发送题目消息
    if not items:
        await send_toast(callback, "🈳 暂无数据")
        return

    new_msg_ids = []
    for item in items:
        cat_name = item.category.name if item.category else "无分类"
        
        # 截取题目内容
        question_text = item.question
        if len(question_text) > 100:
            question_text = question_text[:97] + "..."
            
        # 选项预览（一行显示）
        options_parts = []
        for i, opt in enumerate(item.options):
            prefix = "✅ " if i == item.correct_index else "⚪️ "
            escaped_opt = escape_markdown_v2(opt)
            options_parts.append(f"{prefix}{escaped_opt}")

        escaped_options_text = "   ".join(options_parts)
        
        # 处理标签
        tags_text = ""
        if item.tags:
            escaped_tags = [escape_markdown_v2(tag) for tag in item.tags]
            tags_text = " \\| ".join(escaped_tags)

        caption = (
            f"🆔 `{item.id}` ｜ 🗂️ `{escape_markdown_v2(cat_name)}`｜ 🏷️ {tags_text} ｜ {'🟢 启用' if item.is_active else '🔴 禁用'}\n\n"
            f"💭 *{escape_markdown_v2(question_text)}*\n"
            f"{escaped_options_text}\n\n"
        )

        try:
            msg = await callback.message.answer(
                text=caption,
                reply_markup=get_quiz_question_item_keyboard(item.id, item.is_active),
                parse_mode="MarkdownV2"
            )
            new_msg_ids.append(msg.message_id)

        except Exception as e:
            await callback.message.answer(f"❌ 题目 ID `{item.id}` 加载失败: {e}")

    # 记录新发送的消息ID
    await state.update_data(quiz_list_ids=new_msg_ids)
    await callback.answer()


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":item:question:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def question_item_action(callback: CallbackQuery, session: AsyncSession) -> None:
    """题目单项操作"""
    # 解析参数: admin:quiz:item:question:toggle:123
    try:
        parts = callback.data.split(":")
        action = parts[4]

        if action == "close":
            await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
            return

        item_id = int(parts[5])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    item = await session.get(QuizQuestionModel, item_id)
    if not item:
        await callback.answer("❌ 题目不存在", show_alert=True)
        await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
        return

    if action == "toggle":
        item.is_active = not item.is_active
        await session.commit()

        # 更新消息内容
        cat_name = item.category.name if item.category else "无分类"
        question_text = item.question
        if len(question_text) > 100:
            question_text = question_text[:97] + "..."
            
        # 选项预览（一行显示）
        options_parts = []
        for i, opt in enumerate(item.options):
            prefix = "✅ " if i == item.correct_index else "⚪️ "
            escaped_opt = escape_markdown_v2(opt)
            options_parts.append(f"{prefix}{escaped_opt}")

        escaped_options_text = "   ".join(options_parts)

        # 处理标签
        tags_text = ""
        if item.tags:
            escaped_tags = [escape_markdown_v2(tag) for tag in item.tags]
            tags_text = " \\| ".join(escaped_tags)

        caption = (
            f"🆔 `{item.id}` ｜ 🗂️ `{escape_markdown_v2(cat_name)}`｜ 🏷️ {tags_text} ｜ {'🟢 启用' if item.is_active else '🔴 禁用'}\n\n"
            f"💭 *{escape_markdown_v2(question_text)}*\n"
            f"{escaped_options_text}\n\n"
        )

        with contextlib.suppress(Exception):
            await callback.message.edit_text(
                text=caption,
                reply_markup=get_quiz_question_item_keyboard(item.id, item.is_active),
                parse_mode="MarkdownV2"
            )

        status_text = "🟢 启用" if item.is_active else "🔴 禁用"
        await callback.answer(f"✅ 题目 ID `{item.id}` 已{status_text}")

    elif action == "delete":
        # 软删除
        item.is_deleted = True
        item.is_active = False
        item.deleted_at = now()
        item.deleted_by = callback.from_user.id
        item.remark = f"删除用户 {callback.from_user.full_name} (ID: {callback.from_user.id})"
        await session.commit()
        await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
        await callback.answer("✅ 操作成功！\n题目已删除")
    
    elif action == "edit":
         await callback.answer("🚧 编辑功能开发中...", show_alert=True)
