from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import QuizQuestionModel, QuizImageModel, QuizCategoryModel
from bot.states.admin import QuizAdminState
from bot.utils.permissions import require_admin_feature
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.keyboards.inline.admin import get_quiz_add_cancel_keyboard, get_quiz_add_success_keyboard
from bot.utils.text import escape_markdown_v2
from bot.utils.message import send_toast
from .router import router

from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.services.quiz_service import QuizService

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":add")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def start_quick_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession, main_msg: MainMessageService):
    """开始添加"""
    # 获取可显示的分类列表
    stmt = select(QuizCategoryModel).order_by(QuizCategoryModel.sort_order.asc(), QuizCategoryModel.id.asc())
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
        "第2行：选项A　选项B　选项C　选项D（空格分隔）\n"
        "第3行：正确答案序号（1-4）\n"
        "第4行：分类ID（见下方列表）\n"
        "第5行：标签1　标签2（空格或逗号分隔，必填）\n"
        "第6行：难度系数（1-5，可选，默认1）\n"
        "第7行：图片来源（链接或文字描述，可选）\n"
        "第8行：图片补充说明（可选）`\n\n"
        "*可用分类：*\n"
        f"{cat_text}"
    )
    await main_msg.update_on_callback(callback, text, get_quiz_add_cancel_keyboard())
    
    # 发送示例消息
    example_text = (
        "*📝 示例格式：*\n\n"
        "`LGBT骄傲月是什么时候？\n"
        "3月　6月　9月　12月\n"
        "2\n"
        "15\n"
        "LGBT骄傲月\n"
        "1\n"
        "https://example.com/source\n"
        "这是一张关于骄傲月的图片`"
    )
    
    # 尝试根据示例标签查找图片
    example_image = await QuizService.get_random_image_by_tags(session, ["LGBT骄傲月"])
    
    # 删除按钮
    del_btn = InlineKeyboardBuilder().button(
        text="🗑️ 删除说明", 
        callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":del_msg"
    ).as_markup()

    try:
        if example_image:
             await callback.message.answer_photo(
                 photo=example_image.file_id,
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
        pass # 忽略发送失败

    await state.set_state(QuizAdminState.waiting_for_quick_add)
    await callback.answer()

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":del_msg")
async def delete_example_msg(callback: CallbackQuery):
    """删除示例消息"""
    await callback.message.delete()
    await callback.answer()

@router.message(QuizAdminState.waiting_for_quick_add)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def process_quick_add(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService):
    """处理快捷添加"""
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
            stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == cat_id)
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

        # 保存题目
        quiz = QuizQuestionModel(
            question=question_text,
            options=options,
            correct_index=correct_index,
            difficulty=difficulty,
            reward_base=5,
            reward_bonus=15,
            category_id=category_id,
            tags=tags,
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
                category_id=category_id,
                tags=tags, # 继承题目标签
                description=f"自动添加于题目 {quiz.id}",
                image_source=image_source,
                extra_caption=extra_caption,
                is_active=True,
                created_by=message.from_user.id
            )
            session.add(img)

        await session.commit()

        success_text = (
            f"✅ *题目已添加！*\n"
            f"🆔 ID：`{quiz.id}`\n"
            f"❓ 题目：{escape_markdown_v2(question_text)}\n"
            f"📂 分类：{escape_markdown_v2(category_name)} \\(`{category_id}`\\)\n"
            f"🏷️ 标签：{escape_markdown_v2('，'.join(tags))}\n"
            f"🌟 难度：{difficulty}"
        )
        if image_source:
            success_text += f"\n🔗 来源：{escape_markdown_v2(image_source)}"
            
        await state.clear()
        await main_msg.render(message.from_user.id, success_text, get_quiz_add_success_keyboard())

    except Exception as e:
        await send_toast(message, f"❌ 添加失败: {e}")
