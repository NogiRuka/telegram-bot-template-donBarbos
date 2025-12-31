from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizImageModel, QuizLogModel, QuizQuestionModel
from bot.keyboards.inline.admin import get_quiz_list_keyboard
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA, QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2


@router.callback_query(F.data == QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_list_menu(callback: CallbackQuery, main_msg: MainMessageService) -> None:
    """显示查看列表菜单"""
    text = (
        "*📋 查看列表*\n\n"
        "请选择要查看的内容："
    )
    await main_msg.update_on_callback(callback, text, get_quiz_list_keyboard())
    await callback.answer()


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":list_questions")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_questions(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示题目列表"""
    # 只显示最近 10 条
    stmt = select(QuizQuestionModel).order_by(QuizQuestionModel.id.desc()).limit(10)
    questions = (await session.execute(stmt)).scalars().all()

    msg = "*📋 最近添加的题目 \\(Top 10\\):*\n\n"
    for q in questions:
        cat_name = q.category.name if q.category else "无分类"
        cat = escape_markdown_v2(cat_name)
        ques = escape_markdown_v2(q.question[:20])
        msg += f"ID: {q.id} \\| {cat}\nQ: {ques}\\.\\.\\.\n\n"

    await main_msg.update_on_callback(callback, msg, get_quiz_list_keyboard()) # 返回列表菜单


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":list_images")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_images(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示题图列表"""
    # 只显示最近 10 条
    stmt = select(QuizImageModel).order_by(QuizImageModel.id.desc()).limit(10)
    images = (await session.execute(stmt)).scalars().all()

    msg = "*🖼️ 最近添加的图片 \\(Top 10\\):*\n\n"
    for img in images:
        cat_name = img.category.name if img.category else "无分类"
        cat = escape_markdown_v2(cat_name)
        tags_str = ", ".join(img.tags) if img.tags else ""
        tags = escape_markdown_v2(tags_str)
        msg += f"ID: {img.id} \\| {cat}\nTags: {tags}\n\n"

    await main_msg.update_on_callback(callback, msg, get_quiz_list_keyboard())


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
