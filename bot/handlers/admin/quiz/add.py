from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import QuizQuestionModel, QuizImageModel
from bot.states.admin import QuizAdminState
from bot.utils.permissions import require_admin_feature
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from .router import router

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":add_quick")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def start_quick_add(callback: CallbackQuery, state: FSMContext):
    """开始快捷添加"""
    await callback.message.answer(
        "*➕ 快捷添加题目*\n\n"
        "请发送一张图片（可选），并在 Caption（如果是纯文本则直接发送文本）中按以下格式输入：\n\n"
        "`题目描述\n"
        "选项A 选项B 选项C 选项D\n"
        "正确答案序号\\(1\\-4\\)\n"
        "分类\\(如：漫画，小说，影视，GV\\)\n"
        "标签\\(逗号分隔\\)`\n\n"
        "例如：\n"
        "`这部番的主角是谁？\n"
        "路人甲 鸣人 佐助 小樱\n"
        "2\n"
        "动漫\n"
        "火影忍者,JUMP`",
        parse_mode="MarkdownV2"
    )
    await state.set_state(QuizAdminState.waiting_for_quick_add)
    await callback.answer()

@router.message(QuizAdminState.waiting_for_quick_add)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def process_quick_add(message: Message, state: FSMContext, session: AsyncSession):
    """处理快捷添加"""
    # 获取文本内容
    text = message.caption or message.text
    if not text:
        await message.answer("⚠️ 请输入题目内容。")
        return

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 4:
        await message.answer(
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
            await message.answer(f"⚠️ 选项解析失败，找到 {len(options)} 个选项，需要 4 个。")
            return

        correct_idx_raw = lines[2]
        if not correct_idx_raw.isdigit() or not (1 <= int(correct_idx_raw) <= 4):
            await message.answer("⚠️ 正确答案序号必须是 1-4 的数字。")
            return
        correct_index = int(correct_idx_raw) - 1

        category = lines[3]
        
        tags = []
        if len(lines) > 4:
            tags_line = lines[4]
            tags = [t.strip() for t in tags_line.replace("，", ",").split(",") if t.strip()]

        # 保存题目
        quiz = QuizQuestionModel(
            question=question_text,
            options=options,
            correct_index=correct_index,
            difficulty=1,
            reward_base=5,
            reward_bonus=15,
            category=category,
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
                category=category,
                tags=tags, # 继承题目标签
                description=f"Auto added with quiz {quiz.id}",
                is_active=True
            )
            session.add(img)
        
        await session.commit()
        await message.answer(f"✅ 题目已添加！(ID: {quiz.id})\n分类: {category}\n标签: {tags}")
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ 添加失败: {e}")
