from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_SYMBOL
from bot.database.models import QuizCategoryModel, QuizImageModel, QuizQuestionModel
from bot.keyboards.inline.buttons import BACK_TO_HOME_BUTTON, BACK_TO_PROFILE_BUTTON
from bot.keyboards.inline.constants import USER_QUIZ_SUBMIT_CALLBACK_DATA
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.states.user import UserQuizSubmitState
from bot.utils.message import send_toast
from bot.utils.text import escape_markdown_v2

router = Router(name="user_quiz_submit")

@router.callback_query(F.data == USER_QUIZ_SUBMIT_CALLBACK_DATA)
async def start_quiz_submit(callback: CallbackQuery, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """开始投稿"""
    # 获取可显示的分类列表
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.is_deleted.is_(False)).order_by(QuizCategoryModel.sort_order.asc(), QuizCategoryModel.id.asc())
    categories = (await session.execute(stmt)).scalars().all()

    # 每行 5 个
    lines = []
    for i in range(0, len(categories), 5):
        row = categories[i:i + 5]
        line = "   ".join(
            f"{c.id}\\. {escape_markdown_v2(c.name)}"
            for c in row
        )
        lines.append(line)

    cat_text = "\n".join(lines)

    text = (
        "*✍️ 问答投稿*\n"
        "欢迎为题库贡献题目\\!\n\n"
        f"📸 可发送 1\\-{MAX_QUIZ_IMAGE_BATCH} 张图片\\(可选，纯题图投稿也支持多张\\)\n"
        "✍️ 题目请写在说明中\\(纯文本直接发送即可\\)\n\n"
        "📝 *输入格式说明：*\n"
        "`第1行：题目描述\n"
        "第2行：选项A　选项B　选项C　选项D（空格或逗号分隔）\n"
        "第3行：正确答案序号（1-4）\n"
        "第4行：分类ID（见下方列表）\n"
        "第5行：标签1　标签2（空格或逗号分隔，必填）\n"
        "第6行：难度系数（1-5，可选，默认1）\n"
        "第7行：图片来源（链接或文字描述，可选）\n"
        "第8行：图片补充说明（可选）`\n\n"
        "🖼️ *仅添加题图格式：*\n"
        "`第1行：分类ID\n"
        "第2行：标签1　标签2（必填）\n"
        "第3行：图片来源（可选）\n"
        "第4行：图片补充说明（可选）`\n\n"
        "*📂 可用分类：*\n"
        f"{cat_text}"
    )

    # 键盘：查看示例、取消
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 查看示例", callback_data=f"{USER_QUIZ_SUBMIT_CALLBACK_DATA}:example")
    builder.button(text="❌ 取消", callback_data="user:profile") # 直接返回个人中心
    builder.adjust(1)

    await main_msg.update_on_callback(callback, text, builder.as_markup())
    await state.set_state(UserQuizSubmitState.waiting_for_input)
    await callback.answer()

@router.callback_query(F.data == f"{USER_QUIZ_SUBMIT_CALLBACK_DATA}:example")
async def send_example(callback: CallbackQuery, session: AsyncSession) -> None:
    """发送示例消息"""
    # 尝试从数据库获取 ID 为 1 的题目（示例数据）
    stmt = select(QuizQuestionModel).where(QuizQuestionModel.id == 1)
    result = await session.execute(stmt)
    question = result.scalar_one_or_none()

    del_btn = InlineKeyboardBuilder().button(
        text="🗑️ 删除示例",
        callback_data=f"{USER_QUIZ_SUBMIT_CALLBACK_DATA}:del_msg"
    ).as_markup()

    if not question:
        # 如果数据库没有示例数据，显示默认提示
        await callback.answer("⚠️ 未找到示例数据 (ID: 1)", show_alert=True)
        return

    # 构建示例格式文本
    options_str = "　".join(question.options)
    tags_str = " ".join(question.tags or [])

    # 获取关联的图片
    image_stmt = select(QuizImageModel).where(QuizImageModel.id == 1)
    image_result = await session.execute(image_stmt)
    image = image_result.scalar_one_or_none()

    image_source = ""
    extra_caption = ""

    if image:
        image_source = image.image_source or ""
        extra_caption = image.extra_caption or ""

    # 格式化输出
    example_text = (
        f"`{question.question}\n"
        f"{options_str}\n"
        f"{question.correct_index + 1}\n"
        f"{question.category_id}\n"
        f"{tags_str}\n"
        f"{question.difficulty}\n"
        f"{image_source}\n"
        f"{extra_caption}`"
    )

    try:
        if image:
            await callback.message.answer_photo(
                photo=image.file_id,
                caption=example_text,
                parse_mode="MarkdownV2",
                reply_markup=del_btn
            )
        else:
            await callback.message.answer(
                example_text,
                parse_mode="MarkdownV2",
                reply_markup=del_btn
            )
    except Exception as e:
        logger.error(f"发送示例消息失败: {e}", exc_info=True)
    await callback.answer()

@router.callback_query(F.data == f"{USER_QUIZ_SUBMIT_CALLBACK_DATA}:del_msg")
async def delete_example_msg(callback: CallbackQuery) -> None:
    """删除示例消息"""
    await callback.message.delete()
    await callback.answer()

from bot.utils.quiz import (
    MAX_QUIZ_IMAGE_BATCH,
    QuizParseError,
    build_quiz_image_models,
    ensure_quiz_photo_limit,
    parse_quiz_input,
    resolve_quiz_media_input,
)


@router.message(UserQuizSubmitState.waiting_for_input)
async def process_submit(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    main_msg: MainMessageService,
    album: list[Message] | None = None,
) -> None:
    """处理用户投稿"""
    media_list, photo_messages, _, text = resolve_quiz_media_input(message, album)

    try:
        ensure_quiz_photo_limit(photo_messages)
        # 复用公共解析逻辑
        parsed = await parse_quiz_input(session, text)

        for media in media_list:
            await main_msg.delete_input(media)

        if parsed.get("is_image_only"):
            user_id = message.from_user.id
            extra_data = {
                "submitted_by": user_id,
                "submission_rewarded": True
            }

            if not photo_messages:
                await send_toast(message, "❌ 仅添加题图模式必须发送图片")
                return

            images = build_quiz_image_models(
                photo_messages,
                category_id=parsed["category_id"],
                tags=parsed["tags"],
                description=f"用户 {user_id} 投稿题图",
                image_source=parsed["image_source"],
                extra_caption=parsed["extra_caption"],
                is_active=True,
                created_by=user_id,
                extra=extra_data,
            )
            session.add_all(images)
            await session.flush()

            await CurrencyService.add_currency(
                session=session,
                user_id=user_id,
                amount=3,
                event_type="quiz_submit_base",
                description=f"投稿题图 {len(images)} 张奖励"
            )

            await session.commit()

            try:
                from bot.utils.msg_group import send_group_notification

                user_info = {
                    "user_id": str(user_id),
                    "username": message.from_user.username or "Unknown",
                    "full_name": message.from_user.full_name,
                    "group_name": "QuizSubmit",
                    "action": "Submit",
                }

                reason = (
                    f"投稿了桜之问答题图（{len(images)}张）\n"
                    f"🏷️ {escape_markdown_v2('，'.join(parsed['tags']))}"
                )

                await send_group_notification(message.bot, user_info, reason)
            except Exception as e:
                logger.warning(f"发送群组通知失败: {e}")

            if len(images) == 1:
                success_text = (
                    "✅ *题图投稿成功\\!*\n\n"
                    f"🆔 ID：`{images[0].id}`\n"
                    f"📂 分类：{escape_markdown_v2(parsed['category_name'])} \\(`{parsed['category_id']}`\\)\n"
                    f"🏷️ 标签：{escape_markdown_v2('，'.join(parsed['tags']))}\n"
                    f"🎁 奖励：\\+3 {escape_markdown_v2(CURRENCY_SYMBOL)} 已发放\n"
                )
            else:
                image_ids = "、".join(f"`{img.id}`" for img in images)
                success_text = (
                    "✅ *题图投稿成功\\!*\n\n"
                    f"🆔 ID：{image_ids}\n"
                    f"📂 分类：{escape_markdown_v2(parsed['category_name'])} \\(`{parsed['category_id']}`\\)\n"
                    f"🏷️ 标签：{escape_markdown_v2('，'.join(parsed['tags']))}\n"
                    f"🎁 奖励：\\+3 {escape_markdown_v2(CURRENCY_SYMBOL)} 已发放\n"
                )
            if parsed["image_source"]:
                success_text += f"🔗 来源：{escape_markdown_v2(parsed['image_source'])}\n"
            if parsed["extra_caption"]:
                success_text += f"📄 说明：{escape_markdown_v2(parsed['extra_caption'])}\n"

            await state.clear()
            builder = InlineKeyboardBuilder()
            builder.button(text="✍️ 继续投稿", callback_data=USER_QUIZ_SUBMIT_CALLBACK_DATA)
            builder.row(BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON)
            await main_msg.render(user_id, success_text.rstrip(), builder.as_markup())
            return

        # 保存题目 (默认不启用)
        user_id = message.from_user.id
        extra_data = {
            "submitted_by": user_id,
            "submission_rewarded": True
        }

        quiz = QuizQuestionModel(
            question=parsed["question"],
            options=parsed["options"],
            correct_index=parsed["correct_index"],
            difficulty=parsed["difficulty"],
            reward_base=5,
            reward_bonus=15,
            category_id=parsed["category_id"],
            tags=parsed["tags"],
            is_active=False,  # 默认不启用
            created_by=user_id,
            extra=extra_data
        )
        session.add(quiz)
        await session.flush() # 获取 ID

        # 如果有图片，保存图片并关联
        if photo_messages:
            images = build_quiz_image_models(
                photo_messages,
                category_id=parsed["category_id"],
                tags=parsed["tags"],
                description=f"用户 {user_id} 投稿题目 {quiz.id}",
                image_source=parsed["image_source"],
                extra_caption=parsed["extra_caption"],
                is_active=True,
                created_by=user_id,
                extra=extra_data,
            )
            session.add_all(images)

        # 发放基础奖励
        await CurrencyService.add_currency(
            session=session,
            user_id=user_id,
            amount=3,
            event_type="quiz_submit_base",
            description=f"投稿问答 #{quiz.id} 奖励"
        )

        await session.commit()

        # 通知群组 (使用工具类)
        try:
            from bot.utils.msg_group import send_group_notification

            user_info = {
                "user_id": str(user_id),
                "username": message.from_user.username or "Unknown",
                "full_name": message.from_user.full_name,
                "group_name": "QuizSubmit", # 自定义标签
                "action": "Submit",
            }

            reason = (
                f"投稿了桜之问答（{quiz.id}）\n"
                f"💭 {escape_markdown_v2(parsed['question'])}"
            )

            await send_group_notification(message.bot, user_info, reason)
        except Exception as e:
            logger.warning(f"发送群组通知失败: {e}")

        success_text = (
            f"✅ *投稿成功\\!*\n\n"
            f"❓ 题目：{escape_markdown_v2(parsed['question'])}\n"
            f"🎁 奖励：\\+3 {escape_markdown_v2(CURRENCY_SYMBOL)} 已发放\n"
        )

        # 退出状态
        await state.clear()

        # 返回成功界面 (可以使用通用的返回键盘)
        builder = InlineKeyboardBuilder()
        builder.button(text="✍️ 继续投稿", callback_data=USER_QUIZ_SUBMIT_CALLBACK_DATA)
        builder.row(BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON)

        await main_msg.render(user_id, success_text, builder.as_markup())

    except QuizParseError as e:
        await send_toast(message, f"⚠️ {e}")
    except Exception as e:
        logger.error(f"User submission failed: {e}", exc_info=True)
        await send_toast(message, f"❌ 投稿失败: {e}")
