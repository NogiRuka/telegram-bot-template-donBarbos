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

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":add")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def start_quick_add(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService):
    """开始快捷添加"""
    text = (
        "*➕ 添加题目*\n\n"
        "请发送一张图片（可选），并在 Caption（如果是纯文本则直接发送文本）中按以下格式输入：\n\n"
        "`题目描述\n"
        "选项A 选项B 选项C 选项D\n"
        "正确答案序号\\(1\\-4\\)\n"
        "分类名称或ID\\(如：动漫 或 8\\)\n"
        "标签\\(逗号分隔\\)\n"
        "难度系数\\(1\\-5，默认1\\)`\n\n"
        "例如：\n"
        "`这部番的主角是谁？\n"
        "路人甲 鸣人 佐助 小樱\n"
        "2\n"
        "8\n"
        "火影忍者,JUMP\n"
        "1`"
    )
    await main_msg.update_on_callback(callback, text, get_quiz_add_cancel_keyboard())
    await state.set_state(QuizAdminState.waiting_for_quick_add)
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
    
    # 提取难度 (最后一行如果是数字且在1-5之间)
    difficulty = 1
    if lines and lines[-1].isdigit():
        diff_val = int(lines[-1])
        if 1 <= diff_val <= 5:
            difficulty = diff_val
            lines.pop()

    if len(lines) < 4:
        await send_toast(
            message,
            "⚠️ 格式错误，行数不足。\n"
            "请确保包含：题目、选项、答案序号、分类、标签（可选）。"
        )
        return

    try:
        # 解析
        question_text = lines[0]
        options_text = lines[1]
        
        # 尝试空格分隔
        options = [o for o in options_text.split(" ") if o]
        if len(options) != 4:
            await send_toast(message, f"⚠️ 选项解析失败，找到 {len(options)} 个选项，需要 4 个。")
            return

        correct_idx_raw = lines[2]
        if not correct_idx_raw.isdigit() or not (1 <= int(correct_idx_raw) <= 4):
            await send_toast(message, "⚠️ 正确答案序号必须是 1-4 的数字。")
            return
        correct_index = int(correct_idx_raw) - 1

        category_input = lines[3]
        category_name = category_input
        
        # 如果是数字，尝试查找分类ID
        if category_input.isdigit():
            cat_id = int(category_input)
            stmt = select(QuizCategoryModel.name).where(QuizCategoryModel.id == cat_id)
            result = await session.execute(stmt)
            name = result.scalar_one_or_none()
            if name:
                category_name = name
            else:
                await send_toast(message, f"⚠️ 未找到ID为 {cat_id} 的分类，请检查。")
                return
        
        tags = []
        if len(lines) > 4:
            tags_line = lines[4]
            tags = [t.strip() for t in tags_line.replace("，", ",").split(",") if t.strip()]

        # 保存题目
        quiz = QuizQuestionModel(
            question=question_text,
            options=options,
            correct_index=correct_index,
            difficulty=difficulty,
            reward_base=5,
            reward_bonus=15,
            category=category_name,
            tags=tags,
            is_active=True
        )
        session.add(quiz)
        await session.flush() # 获取 ID

        # 如果有图片，保存图片并关联
        if message.photo:
            photo = message.photo[-1]
            img = QuizImageModel(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                category=category_name,
                tags=tags, # 继承题目标签
                description=f"自动添加于题目 {quiz.id}",
                is_active=True
            )
            session.add(img)

        await session.commit()

        success_text = (
            f"✅ *题目已添加！* \\(ID: `{quiz.id}`\\)\n"
            f"� 题目：{escape_markdown_v2(question_text)}\n"
            f"�📂 分类：{escape_markdown_v2(category_name)}\n"
            f"🏷️ 标签：{escape_markdown_v2(', '.join(tags))}\n"
            f"🌟 难度：{difficulty}"
        )
        await state.clear()
        await main_msg.render(message.from_user.id, success_text, get_quiz_add_success_keyboard())

    except Exception as e:
        await send_toast(message, f"❌ 添加失败: {e}")
