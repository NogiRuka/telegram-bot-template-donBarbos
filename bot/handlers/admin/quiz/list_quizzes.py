from math import ceil

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizQuestionModel
from bot.keyboards.inline.admin import (
    QUIZ_ADMIN_CALLBACK_DATA,
)
from bot.keyboards.inline.buttons import BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA, QUIZ_ADMIN_LIST_QUIZZES_LABEL
from bot.services.main_message import MainMessageService
from bot.services.quiz_service import QuizService
from bot.states.admin import QuizAdminState
from bot.utils.message import clear_message_list_from_state, safe_delete_message, send_toast
from bot.utils.permissions import require_admin_feature


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


def build_question_keyboard(options: list[str], question_id: int | None = None, is_review_needed: bool = False, correct_index: int = -1) -> InlineKeyboardMarkup:
    """构建问题选项键盘 (模拟用户端)"""
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(options):
        # 标记正确答案
        if i == correct_index:
            option = f"{option} ✅"

        # 使用特定回调以便识别，或者仅仅展示用 ignore
        # 这里为了模拟真实感，可以使用类似真实的回调，或者 dummy callback
        builder.button(text=option, callback_data=f"ignore:quiz_preview:{i}")
    builder.adjust(2) # 每行2个选项，和真实答题保持一致

    # 添加审核按钮
    if is_review_needed and question_id is not None:
        builder.row(
            InlineKeyboardButton(text="❌ 拒绝", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:reject:{question_id}"),
            InlineKeyboardButton(text="✅ 通过", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:approve:{question_id}")
        )

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
            is_review_needed = question.extra and question.extra.get("submitted_by") and not question.extra.get("approval_rewarded")
            keyboard = build_question_keyboard(
                question.options,
                question_id=question.id,
                is_review_needed=bool(is_review_needed),
                correct_index=question.correct_index
            )

            # 4. 发送消息
            sent = False
            if image:
                try:
                    msg = await callback.message.answer_photo(
                        photo=image.file_id,
                        caption=caption,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    sent = True
                except TelegramBadRequest as e:
                    logger.warning(f"题目 #{question.id} 图片发送失败 (File ID: {image.file_id}): {e}")
                    # 如果 file_id 失效，尝试使用 image_source (如果是 URL)
                    if image.image_source and image.image_source.startswith("http"):
                        try:
                            msg = await callback.message.answer_photo(
                                photo=image.image_source,
                                caption=caption,
                                reply_markup=keyboard,
                                parse_mode="HTML"
                            )
                            sent = True
                        except Exception as e2:
                            logger.warning(f"题目 #{question.id} 图片 URL 发送也失败: {e2}")

            # 如果没有图片或图片发送失败，发送纯文本
            if not sent:
                logger.info(f"题目 #{question.id} 无图片或图片发送失败，发送纯文本")
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
            except Exception as e:
                logger.error(f"题目 #{question.id} 渲染失败并通知用户失败: {e}")

    # 记录新发送的消息ID
    await state.update_data(quiz_list_ids=new_msg_ids)
    await callback.answer()


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":list:view:approve:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def approve_quiz(callback: CallbackQuery, session: AsyncSession) -> None:
    """审核题目"""
    try:
        parts = callback.data.split(":")
        # 修正: 回调格式为 admin:quiz:list:view:quiz:approve:{question_id}
        # admin(0):quiz(1):list(2):view(3):approve(4):{question_id}(5)
        question_id = int(parts[5])
    except (IndexError, ValueError):
        logger.error(f"参数解析失败: {callback.data}")
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    item = await session.get(QuizQuestionModel, question_id)
    if not item:
        await callback.answer("❌ 题目不存在", show_alert=True)
        return

    # 检查是否为用户投稿且未发放审核奖励
    if item.extra:
        submitted_by = item.extra.get("submitted_by")
        approval_rewarded = item.extra.get("approval_rewarded")

        if submitted_by and not approval_rewarded:
            # 发放奖励
            from bot.core.constants import CURRENCY_SYMBOL
            from bot.services.currency import CurrencyService
            from bot.utils.text import escape_markdown_v2

            try:
                await CurrencyService.add_currency(
                    session=session,
                    user_id=submitted_by,
                    amount=5,
                    event_type="quiz_submit_approve",
                    description=f"投稿题目 #{item.id} 审核通过奖励"
                )

                # 更新状态
                item.extra = dict(item.extra) # 复制一份以触发更新
                item.extra["approval_rewarded"] = True
                item.is_active = True # 审核通过自动启用

                await session.commit()

                # 1. 通知用户 (私聊)
                try:
                    await callback.bot.send_message(
                        submitted_by,
                        f"🎉 *恭喜\\!* 您投稿的题目 *{escape_markdown_v2(item.question)}* 已通过审核并启用\\!\n"
                        f"🎁 获得额外奖励：\\+5 {escape_markdown_v2(CURRENCY_SYMBOL)}",
                        parse_mode="MarkdownV2"
                    )
                except Exception as e:
                     # 用户可能屏蔽了机器人
                    logger.warning(f"通知用户 {submitted_by} 失败 (可能已屏蔽机器人): {e}")

                await callback.answer("✅ 审核通过！奖励已发放，题目已启用。")

                # 刷新键盘，移除审核按钮
                is_review_needed = False
                keyboard = build_question_keyboard(item.options, question_id=item.id, is_review_needed=is_review_needed)
                with contextlib.suppress(Exception):
                     await callback.message.edit_reply_markup(reply_markup=keyboard)

            except Exception as e:
                await callback.answer(f"⚠️ 奖励发放失败: {e}", show_alert=True)
                return
        else:
             await callback.answer("⚠️ 该题目已审核或非用户投稿", show_alert=True)
             # 尝试刷新键盘
             is_review_needed = False
             keyboard = build_question_keyboard(item.options, question_id=item.id, is_review_needed=is_review_needed)
             with contextlib.suppress(Exception):
                 await callback.message.edit_reply_markup(reply_markup=keyboard)
             return
    else:
        await callback.answer("⚠️ 该题目非用户投稿", show_alert=True)
        return


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":list:view:reject:"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def reject_quiz_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """开始拒绝流程"""
    try:
        parts = callback.data.split(":")
        question_id = int(parts[5])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    item = await session.get(QuizQuestionModel, question_id)
    if not item:
        await callback.answer("❌ 题目不存在", show_alert=True)
        return

    # 保存上下文
    await state.update_data(reject_question_id=question_id, reject_msg_id=callback.message.message_id)
    await state.set_state(QuizAdminState.waiting_for_reject_reason)

    # 提示输入原因
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ 取消", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:reject_cancel")

    await callback.message.reply("📝 请输入拒绝原因:", reply_markup=kb.as_markup())
    await callback.answer()



@router.callback_query(F.data == f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:reject_cancel")
async def reject_quiz_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """取消拒绝"""
    await state.set_state(None) # 清除状态但保留数据，或者全清
    # 删除提示消息
    await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
    await callback.answer("已取消")

@router.message(QuizAdminState.waiting_for_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """处理拒绝原因"""
    reason = message.text.strip()
    if not reason:
        await send_toast(message, "⚠️ 原因不能为空")
        return

    data = await state.get_data()
    question_id = data.get("reject_question_id")
    # msg_id = data.get("reject_msg_id") # 原消息ID，用于刷新键盘

    # 清理输入消息和提示消息
    await safe_delete_message(message.bot, message.chat.id, message.message_id)
    # 提示消息通常是上一条，这里简单处理，不强求删除提示消息，因为上面有取消按钮会删

    item = await session.get(QuizQuestionModel, question_id)
    if not item:
        await send_toast(message, "❌ 题目不存在")
        await state.clear()
        return

    if item.extra:
        submitted_by = item.extra.get("submitted_by")

        # 标记为已审核（虽然是被拒绝）
        # 也可以选择删除题目，或者保留但标记为拒绝
        # 这里逻辑：标记为已审核（不发奖励），并设为禁用（防止被误启用）
        item.extra = dict(item.extra)
        item.extra["approval_rewarded"] = True # 借用字段表示已处理
        item.extra["reject_reason"] = reason
        item.is_active = False

        await session.commit()

        # 1. 通知用户 (私聊)
        try:
            from bot.utils.text import escape_markdown_v2
            await message.bot.send_message(
                submitted_by,
                f"⚠️ *很遗憾*，您投稿的题目 *{escape_markdown_v2(item.question)}* 未通过审核。\n"
                f"📝 原因：{escape_markdown_v2(reason)}",
                parse_mode="MarkdownV2"
            )
        except Exception:
            logger.error(f"向用户 {submitted_by} 发送拒绝通知失败: {e}")

        await send_toast(message, "✅ 已拒绝该投稿")

    await state.clear()
