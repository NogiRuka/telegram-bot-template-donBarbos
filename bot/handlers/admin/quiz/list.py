import contextlib
from math import ceil

from aiogram import Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizImageModel, QuizLogModel, QuizQuestionModel
from bot.keyboards.inline.admin import (
    get_quiz_list_keyboard,
    get_quiz_question_item_keyboard,
    get_quiz_question_list_pagination_keyboard,
    get_quiz_image_list_pagination_keyboard,
    get_quiz_image_item_keyboard,
)
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA, QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.datetime import now
from bot.utils.message import safe_delete_message, send_toast
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2


async def _clear_quiz_list(state: FSMContext, bot: Bot, chat_id: int) -> None:
    """清理已发送的列表消息"""
    data = await state.get_data()
    msg_ids = data.get("quiz_list_ids", [])
    if not msg_ids:
        return

    for msg_id in msg_ids:
        await safe_delete_message(bot, chat_id, msg_id)

    await state.update_data(quiz_list_ids=[])


@router.callback_query(F.data == QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_list_menu(callback: CallbackQuery, main_msg: MainMessageService, state: FSMContext) -> None:
    """显示查看列表菜单"""
    # 清理之前可能存在的列表
    if callback.message:
        await _clear_quiz_list(state, callback.bot, callback.message.chat.id)

    text = (
        "*📋 查看列表*\n\n"
        "请选择要查看的内容："
    )
    await main_msg.update_on_callback(callback, text, get_quiz_list_keyboard())
    await callback.answer()


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


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":list:view:image:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_images_view(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """显示题图列表（分页）"""
    # 解析参数: admin:quiz:list:view:image:1:5
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
    count_stmt = select(func.count()).select_from(QuizImageModel).where(QuizImageModel.is_deleted.is_(False))
    total_count = (await session.execute(count_stmt)).scalar_one()
    total_pages = ceil(total_count / limit) if total_count > 0 else 1

    # 如果页码超出范围则调整
    page = min(page, total_pages)
    page = max(page, 1)

    # 查询数据
    stmt = (
        select(QuizImageModel)
        .where(QuizImageModel.is_deleted.is_(False))
        .order_by(QuizImageModel.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = (await session.execute(stmt)).scalars().all()

    # 更新控制消息
    text = (
        f"*🖼️ 题图列表*\n"
        f"共 {total_count} 条，当前第 {page}/{total_pages} 页"
    )
    await main_msg.update_on_callback(
        callback,
        text,
        get_quiz_image_list_pagination_keyboard(page, total_pages, limit)
    )

    # 发送图片消息
    if not items:
        await send_toast(callback, "🈳 暂无数据")
        return

    new_msg_ids = []
    for item in items:
        cat_name = item.category.name if item.category else "无分类"
        
        # 处理标签
        tags_text = ""
        if item.tags:
            escaped_tags = [escape_markdown_v2(tag) for tag in item.tags]
            tags_text = " \\| ".join(escaped_tags)

        extra = "无"
        if item.image_source:
            if item.image_source.startswith("http"):
                link_text = item.extra_caption.strip() if item.extra_caption else "链接"
                extra = f"[{escape_markdown_v2(link_text)}]({item.image_source})"
            else:
                extra = escape_markdown_v2(item.image_source)
        
        caption = (
            f"🆔 `{item.id}` ｜ 🗂️ `{escape_markdown_v2(cat_name)}`｜ 🏷️ {tags_text} ｜ {'🟢 启用' if item.is_active else '🔴 禁用'}\n\n"
            f"�️ {extra}\n"
        )

        try:
            msg = await callback.message.answer_photo(
                photo=item.file_id,
                caption=caption,
                reply_markup=get_quiz_image_item_keyboard(item.id, item.is_active),
                parse_mode="MarkdownV2"
            )
            new_msg_ids.append(msg.message_id)

        except Exception as e:
            await callback.message.answer(f"❌ 图片 ID `{item.id}` 加载失败: {e}")

    # 记录新发送的消息ID
    await state.update_data(quiz_list_ids=new_msg_ids)
    await callback.answer()


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":item:image:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def image_item_action(callback: CallbackQuery, session: AsyncSession) -> None:
    """题图单项操作"""
    # 解析参数: admin:quiz:item:image:toggle:123
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

    item = await session.get(QuizImageModel, item_id)
    if not item:
        await callback.answer("❌ 图片不存在", show_alert=True)
        await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
        return

    if action == "toggle":
        item.is_active = not item.is_active
        await session.commit()

        # 更新消息内容
        cat_name = item.category.name if item.category else "无分类"
        
        tags_text = ""
        if item.tags:
            escaped_tags = [escape_markdown_v2(tag) for tag in item.tags]
            tags_text = " \\| ".join(escaped_tags)
            
        extra = "无"
        if item.image_source:
            if item.image_source.startswith("http"):
                link_text = item.extra_caption.strip() if item.extra_caption else "链接"
                extra = f"[{escape_markdown_v2(link_text)}]({item.image_source})"
            else:
                extra = escape_markdown_v2(item.image_source)
        
        caption = (
            f"🆔 `{item.id}` ｜ 🗂️ `{escape_markdown_v2(cat_name)}`｜ 🏷️ {tags_text} ｜ {'🟢 启用' if item.is_active else '🔴 禁用'}\n\n"
            f"�️ {extra}\n"
        )

        with contextlib.suppress(Exception):
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_quiz_image_item_keyboard(item.id, item.is_active),
                parse_mode="MarkdownV2"
            )

        status_text = "🟢 启用" if item.is_active else "🔴 禁用"
        await callback.answer(f"✅ 图片 ID `{item.id}` 已{status_text}")

    elif action == "delete":
        # 软删除
        item.is_deleted = True
        item.is_active = False
        item.deleted_at = now()
        item.deleted_by = callback.from_user.id
        item.remark = f"删除用户 {callback.from_user.full_name} (ID: {callback.from_user.id})"
        await session.commit()
        await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
        await callback.answer("✅ 操作成功！\n图片已删除")


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":list_logs")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_logs(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示问答记录列表"""
    # 只显示最近 10 条
    stmt = select(QuizLogModel).order_by(QuizLogModel.id.desc()).limit(10)
    logs = (await session.execute(stmt)).scalars().all()

    msg = "*📜 最近问答记录 \\(Top 10\\):*\n\n"
    for log in logs:
        status = "✅ 正确" if log.is_correct else "❌ 错误"
        user_id = log.user_id
        msg += f"ID: {log.id} \\| 用户: {user_id}\n结果: {status}\n\n"

    await main_msg.update_on_callback(callback, msg, get_quiz_list_keyboard())
