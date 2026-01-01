from math import ceil

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import QuizImageModel, QuizQuestionModel
from bot.utils.permissions import require_admin_feature
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.admin import (
    QUIZ_ADMIN_CALLBACK_DATA,
)
from bot.keyboards.inline.buttons import BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA, QUIZ_ADMIN_LIST_QUIZZES_LABEL
from bot.services.main_message import MainMessageService
from bot.services.quiz_service import QuizService
from bot.utils.message import clear_message_list_from_state, send_toast
from .router import router

def get_quiz_list_pagination_keyboard(page: int, total_pages: int, limit: int = 5) -> InlineKeyboardMarkup:
    """生成分页键盘"""
    builder = InlineKeyboardBuilder()

    # 上一页
    if page > 1:
        builder.button(
            text="⬅️ 上一页",
            callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:quiz:{page - 1}:{limit}"
        )
    else:
        builder.button(text="⛔️", callback_data="ignore")
    
    # 页码指示 (Toggle limit)
    next_limit = 10 if limit == 5 else (20 if limit == 10 else 5)
    builder.button(
        text=f"{page}/{total_pages} (每页{limit:02d}条)",
        callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:quiz:1:{next_limit}"
    )

    # 下一页
    if page < total_pages:
        builder.button(
            text="下一页 ➡️",
            callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:quiz:{page + 1}:{limit}"
        )
    else:
        builder.button(text="⛔️", callback_data="ignore")
    
    builder.adjust(3)
    
    # 返回按钮
    builder.row(
        InlineKeyboardButton(text="🔙 返回列表菜单", callback_data=QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA),
        BACK_TO_HOME_BUTTON
    )
    
    return builder.as_markup()


def build_question_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    """构建问题选项键盘 (模拟用户端)"""
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(options):
        # 使用特定回调以便识别，或者仅仅展示用 ignore
        # 这里为了模拟真实感，可以使用类似真实的回调，或者 dummy callback
        builder.button(text=option, callback_data=f"ignore:quiz_preview:{i}")
    builder.adjust(2) # 每行2个选项，和真实答题保持一致
    return builder.as_markup()


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":list:view:quiz:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_quizzes_view(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """显示问题预览列表（分页，展示真实样式）"""
    # 解析参数: admin:quiz:list:view:quiz:1:5
    try:
        parts = callback.data.split(":")
        page = int(parts[5])
        limit = int(parts[6])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    # 先清理旧消息
    if callback.message:
        await clear_message_list_from_state(state, callback.bot, callback.message.chat.id, "quiz_list_ids")

    # 计算总数
    count_stmt = select(func.count()).select_from(QuizQuestionModel)
    total_count = (await session.execute(count_stmt)).scalar_one()
    total_pages = ceil(total_count / limit) if total_count > 0 else 1

    # 如果页码超出范围则调整
    page = min(page, total_pages)
    page = max(page, 1)

    # 查询数据
    stmt = (
        select(QuizQuestionModel)
        .order_by(QuizQuestionModel.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    questions = (await session.execute(stmt)).scalars().all()

    # 更新控制消息
    text = (
        f"*{QUIZ_ADMIN_LIST_QUIZZES_LABEL}*\n"
        f"共 {total_count} 题，当前第 {page}/{total_pages} 页\n"
        f"⚠️ 点击选项无实际效果"
    )
    await main_msg.update_on_callback(
        callback,
        text,
        get_quiz_list_pagination_keyboard(page, total_pages, limit)
    )

    if not questions:
        await callback.answer("🈳 暂无数据")
        return

    new_msg_ids = []
    for question in questions:
        try:
            # 1. 尝试根据 tag 查找图片
            image = await QuizService.get_random_image_by_tags(session, question.tags)
            
            # 2. 构建 Caption
            # 这里的 timeout_sec 可以取默认配置或者 question 里的配置(如果有)
            # 为了预览真实效果，从配置取默认值
            # 由于 QuizService.build_quiz_caption 内部会处理 session -> config，这里传入 session 即可
            caption = await QuizService.build_quiz_caption(
                question=question,
                image=image,
                session=session,
                title=f"桜之问答 #{question.id}"
            )

            # 3. 构建键盘
            keyboard = build_question_keyboard(question.options)

            # 4. 发送消息
            if image:
                msg = await callback.message.answer_photo(
                    photo=image.file_id,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                # 如果没有图片，尝试用 image_url (如果有扩展字段) 或者纯文本
                # QuizQuestionModel 没有 image_url 字段，只有 extra
                # 按照逻辑，如果没有匹配到图片，就发纯文本
                msg = await callback.message.answer(
                    text=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            new_msg_ids.append(msg.message_id)

        except Exception as e:
            try:
                msg = await callback.message.answer(
                    text=f"⚠️ 题目 #{question.id} 渲染失败: {e}",
                    parse_mode="HTML"
                )
                new_msg_ids.append(msg.message_id)
            except Exception:
                pass

    # 记录新发送的消息ID
    await state.update_data(quiz_list_ids=new_msg_ids)
    await callback.answer()
