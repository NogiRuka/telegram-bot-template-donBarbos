from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_SYMBOL
from bot.database.models import QuizCategoryModel, QuizImageModel, QuizQuestionModel
from bot.keyboards.inline.buttons import BACK_TO_ACCOUNT_BUTTON
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
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.is_deleted == False).order_by(QuizCategoryModel.sort_order.asc(), QuizCategoryModel.id.asc())
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
        "*✍️ 问答投稿*\n\n"
        "欢迎为题库贡献题目\\! 投稿一经录用将获得额外精粹奖励\\。\n\n"
        "📸 可发送一张图片\\(可选\\)\n"
        "✍️ 题目请写在说明中\\(纯文本直接发送即可\\)\n\n"
        "📝 *输入格式说明：*\n"
        "`第1行：题目描述\n"
        "第2行：选项A　选项B　选项C　选项D（空格分隔）\n"
        "第3行：正确答案序号（1-4）\n"
        "第4行：分类ID（见下方列表）\n"
        "第5行：标签1　标签2（空格或逗号分隔，必填）\n"
        "第6行：难度系数（1-5，可选，默认1）\n"
        "第7行：图片来源（链接或文字描述，可选）\n"
        "第8行：图片补充说明（可选）`\n\n"
        "*可用分类：*\n"
        f"{cat_text}\n\n"
        "*奖励说明：*\n"
        f"🎁 投稿成功：\\+3 {escape_markdown_v2(CURRENCY_SYMBOL)}\n"
        f"🎁 审核通过：\\+5 {escape_markdown_v2(CURRENCY_SYMBOL)}"
    )

    # 键盘：查看示例、返回
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 查看示例", callback_data=f"{USER_QUIZ_SUBMIT_CALLBACK_DATA}:example")
    builder.row(BACK_TO_ACCOUNT_BUTTON)

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
    except Exception:
        logger.error("发送示例消息失败", exc_info=True)
        await callback.message.answer(
             "❌ 发送失败，请检查图片 ID 是否有效",
             reply_markup=del_btn
        )
    await callback.answer()

@router.callback_query(F.data == f"{USER_QUIZ_SUBMIT_CALLBACK_DATA}:del_msg")
async def delete_example_msg(callback: CallbackQuery) -> None:
    """删除示例消息"""
    await callback.message.delete()
    await callback.answer()

@router.message(UserQuizSubmitState.waiting_for_input)
async def process_submit(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理用户投稿"""
    # 删除用户输入
    await main_msg.delete_input(message)

    # 获取文本内容
    text = message.caption or message.text
    if not text:
        await send_toast(message, "⚠️ 请输入题目内容。")
        return

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 至少需要前5行 (题目, 选项, 答案, 分类, 标签)
    if len(lines) < 5:
        await send_toast(
            message,
            "⚠️ 格式错误，行数不足。\n"
            "请确保至少包含：题目、选项、答案序号、分类、标签。"
        )
        return

    try:
        # 1. 题目
        question_text = lines[0]

        # 2. 选项
        options_text = lines[1]
        options = [o for o in options_text.replace("　", " ").split(" ") if o]
        if len(options) != 4:
            await send_toast(message, f"⚠️ 选项解析失败，找到 {len(options)} 个选项，需要 4 个。")
            return

        # 3. 答案
        correct_idx_raw = lines[2]
        if not correct_idx_raw.isdigit() or not (1 <= int(correct_idx_raw) <= 4):
            await send_toast(message, "⚠️ 正确答案序号必须是 1-4 的数字。")
            return
        correct_index = int(correct_idx_raw) - 1

        # 4. 分类
        category_input = lines[3]
        category_id = None
        category_name = "未知"
        if category_input.isdigit():
            cat_id = int(category_input)
            stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == cat_id, QuizCategoryModel.is_deleted == False)
            result = await session.execute(stmt)
            cat = result.scalar_one_or_none()
            if cat:
                category_id = cat.id
                category_name = cat.name
            else:
                await send_toast(message, f"⚠️ 未找到ID为 {cat_id} 的分类。")
                return
        else:
            await send_toast(message, "⚠️ 分类必须填写ID（数字）。")
            return

        # 5. 标签 (必填)
        tags_line = lines[4].strip()
        tags = []

        # 统一中文逗号
        tags_line = tags_line.replace("，", ",")

        if "," in tags_line:
            # 有逗号，按逗号分隔，保留空格
            tags = [t.strip() for t in tags_line.split(",") if t.strip()]
        else:
            # 无逗号，按空格分隔（支持全角/半角空格）
            tags_line = tags_line.replace("　", " ")
            tags = [t.strip() for t in tags_line.split() if t.strip()]

        if not tags:
             await send_toast(message, "⚠️ 标签不能为空。")
             return

        # 6. 难度 (可选)
        difficulty = 1
        if len(lines) > 5 and lines[5].isdigit():
            diff_val = int(lines[5])
            if 1 <= diff_val <= 5:
                difficulty = diff_val

        # 7. 图片来源 (可选)
        image_source = None
        if len(lines) > 6:
            image_source = lines[6]

        # 8. 图片补充说明 (可选)
        extra_caption = None
        if len(lines) > 7:
            extra_caption = lines[7]

        # 保存题目 (默认不启用)
        user_id = message.from_user.id
        extra_data = {
            "submitted_by": user_id,
            "submission_rewarded": True
        }

        quiz = QuizQuestionModel(
            question=question_text,
            options=options,
            correct_index=correct_index,
            difficulty=difficulty,
            reward_base=5,
            reward_bonus=15,
            category_id=category_id,
            tags=tags,
            is_active=False,  # 默认不启用
            created_by=user_id,
            extra=extra_data
        )
        session.add(quiz)
        await session.flush() # 获取 ID

        # 如果有图片，保存图片并关联
        if message.photo:
            photo = message.photo[-1]
            img = QuizImageModel(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                category_id=category_id,
                tags=tags, # 继承题目标签
                description=f"用户 {user_id} 投稿题目 {quiz.id}",
                image_source=image_source,
                extra_caption=extra_caption,
                is_active=False, # 默认不启用
                created_by=user_id,
                extra=extra_data
            )
            session.add(img)

        # 发放基础奖励
        await CurrencyService.add_balance(session, user_id, 3, f"投稿问答 #{quiz.id} 奖励")

        await session.commit()

        success_text = (
            f"✅ *投稿成功\\!*\n\n"
            f"🆔 ID：`{quiz.id}`\n"
            f"❓ 题目：{escape_markdown_v2(question_text)}\n"
            f"🎁 基础奖励：\\+3 {escape_markdown_v2(CURRENCY_SYMBOL)} 已发放\n"
            f"⏳ 题目审核通过后将额外获得 \\+5 {escape_markdown_v2(CURRENCY_SYMBOL)}\n"
        )
        
        # 退出状态
        await state.clear()
        
        # 返回成功界面 (可以使用通用的返回键盘)
        builder = InlineKeyboardBuilder()
        builder.button(text="✍️ 继续投稿", callback_data=USER_QUIZ_SUBMIT_CALLBACK_DATA)
        builder.row(BACK_TO_ACCOUNT_BUTTON)
        
        await main_msg.render(user_id, success_text, builder.as_markup())

    except Exception as e:
        logger.error(f"User submission failed: {e}", exc_info=True)
        await send_toast(message, f"❌ 投稿失败: {e}")
