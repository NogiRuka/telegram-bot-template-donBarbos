from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizCategoryModel, QuizImageModel, QuizQuestionModel
from bot.keyboards.inline.admin import get_quiz_add_cancel_keyboard, get_quiz_add_success_keyboard
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.services.quiz_service import QuizService
from bot.states.admin import QuizAdminState
from bot.utils.message import send_toast
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":add")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def start_quick_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """开始添加"""
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
        "*➕ 添加题目*\n\n"
        "📸 可发送一张图片（可选）\n"
        "✍️ 题目请写在说明中（纯文本直接发送即可）\n\n"
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
        "*可用分类：*\n"
        f"{cat_text}"
    )
    await main_msg.update_on_callback(callback, text, get_quiz_add_cancel_keyboard())
    await state.set_state(QuizAdminState.waiting_for_quick_add)
    await callback.answer()

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":send_example")
async def send_example(callback: CallbackQuery, session: AsyncSession) -> None:
    """发送示例消息"""
    # 尝试从数据库获取 ID 为 1 的题目（示例数据）
    stmt = select(QuizQuestionModel).where(QuizQuestionModel.id == 1)
    result = await session.execute(stmt)
    question = result.scalar_one_or_none()
    
    del_btn = InlineKeyboardBuilder().button(
        text="🗑️ 删除示例",
        callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":del_msg"
    ).as_markup()

    if not question:
        # 如果数据库没有示例数据，显示默认提示
        await callback.answer("⚠️ 未找到示例数据 (ID: 1)", show_alert=True)
        return

    # 构建示例格式文本
    # 注意：选项之间使用全角空格
    options_str = "　".join(question.options)
    tags_str = " ".join(question.tags or [])
    
    # 获取关联的图片
    # 尝试查找 ID 为 1 的图片，或者通过 tags 查找
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

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":del_msg")
async def delete_example_msg(callback: CallbackQuery) -> None:
    """删除示例消息"""
    await callback.message.delete()
    await callback.answer()

from bot.utils.quiz import parse_quiz_input, QuizParseError

@router.message(QuizAdminState.waiting_for_quick_add)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def process_quick_add(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理快捷添加"""
    # 删除用户输入
    await main_msg.delete_input(message)

    # 获取文本内容
    text = message.caption or message.text
    
    try:
        # 复用公共解析逻辑
        parsed = await parse_quiz_input(session, text)
        
        # 判断是否为仅添加题图模式
        if parsed.get("is_image_only"):
            if not message.photo:
                await callback.message.answer("❌ 仅添加题图模式必须发送图片")
                return

            photo = message.photo[-1]
            img = QuizImageModel(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                category_id=parsed["category_id"],
                tags=parsed["tags"],
                description=f"手动添加题图",
                image_source=parsed["image_source"],
                extra_caption=parsed["extra_caption"],
                is_active=True,
                created_by=message.from_user.id
            )
            session.add(img)
            await session.commit()

            success_text = (
                f"✅ *题图已添加！*\n"
                f"🆔 ID：`{img.id}`\n"
                f"📂 分类：{escape_markdown_v2(parsed['category_name'])} \\(`{parsed['category_id']}`\\)\n"
                f"🏷️ 标签：{escape_markdown_v2('，'.join(parsed['tags']))}"
            )
            if parsed["image_source"]:
                success_text += f"\n🔗 来源：{escape_markdown_v2(parsed['image_source'])}"
            if parsed["extra_caption"]:
                success_text += f"\n📄 说明：{escape_markdown_v2(parsed['extra_caption'])}"
            
            await state.clear()
            await main_msg.render(message.from_user.id, success_text, get_quiz_add_success_keyboard())

        # 保存题目
        quiz = QuizQuestionModel(
            question=parsed["question"],
            options=parsed["options"],
            correct_index=parsed["correct_index"],
            difficulty=parsed["difficulty"],
            reward_base=5,
            reward_bonus=15,
            category_id=parsed["category_id"],
            tags=parsed["tags"],
            is_active=True,
            created_by=message.from_user.id
        )
        session.add(quiz)
        await session.flush() # 获取 ID

        # 如果有图片，保存图片并关联
        if message.photo:
            photo = message.photo[-1]
            img = QuizImageModel(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                category_id=parsed["category_id"],
                tags=parsed["tags"], # 继承题目标签
                description=f"自动添加于题目 {quiz.id}",
                image_source=parsed["image_source"],
                extra_caption=parsed["extra_caption"],
                is_active=True,
                created_by=message.from_user.id
            )
            session.add(img)

        await session.commit()

        success_text = (
            f"✅ *题目已添加！*\n"
            f"🆔 ID：`{quiz.id}`\n"
            f"❓ 题目：{escape_markdown_v2(parsed['question'])}\n"
            f"📂 分类：{escape_markdown_v2(parsed['category_name'])} \\(`{parsed['category_id']}`\\)\n"
            f"🏷️ 标签：{escape_markdown_v2('，'.join(parsed['tags']))}\n"
            f"🌟 难度：{parsed['difficulty']}"
        )
        if parsed["image_source"]:
            success_text += f"\n🔗 来源：{escape_markdown_v2(parsed['image_source'])}"
        if parsed["extra_caption"]:
            success_text += f"\n📄 说明：{escape_markdown_v2(parsed['extra_caption'])}"

        await state.clear()
        await main_msg.render(message.from_user.id, success_text, get_quiz_add_success_keyboard())

    except QuizParseError as e:
        await send_toast(message, f"⚠️ {e}")
    except Exception as e:
        await send_toast(message, f"❌ 添加失败: {e}")
