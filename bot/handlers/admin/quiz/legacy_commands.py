from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import QuizQuestionModel, QuizImageModel
from bot.states.admin import QuizAdminState
from .router import router

@router.message(Command("add_quiz"))
async def cmd_add_quiz(message: Message, state: FSMContext):
    """添加题目"""
    await message.answer("请输入题目描述：")
    await state.set_state(QuizAdminState.waiting_for_question)

@router.message(QuizAdminState.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text)
    await message.answer("请输入4个选项，用换行符分隔：\n例如：\n选项A\n选项B\n选项C\n选项D")
    await state.set_state(QuizAdminState.waiting_for_options)

@router.message(QuizAdminState.waiting_for_options)
async def process_options(message: Message, state: FSMContext):
    text = message.text or ""
    options = [opt.strip() for opt in text.split("\n") if opt.strip()]
    
    if len(options) != 4:
        await message.answer("⚠️ 请严格输入4个选项，每行一个。")
        return

    await state.update_data(options=options)
    
    # 构建选项预览
    msg = "请输入正确选项的序号 (1-4)：\n"
    for i, opt in enumerate(options, 1):
        msg += f"{i}. {opt}\n"
        
    await message.answer(msg)
    await state.set_state(QuizAdminState.waiting_for_correct_index)

@router.message(QuizAdminState.waiting_for_correct_index)
async def process_correct_index(message: Message, state: FSMContext):
    try:
        idx = int(message.text)
        if not (1 <= idx <= 4):
            raise ValueError
        
        # 存储为 0-based index
        await state.update_data(correct_index=idx - 1)
        
        await message.answer("请输入难度等级 (1-5，默认1)：")
        await state.set_state(QuizAdminState.waiting_for_difficulty)
    except ValueError:
        await message.answer("⚠️ 请输入 1-4 之间的数字。")

@router.message(QuizAdminState.waiting_for_difficulty)
async def process_difficulty(message: Message, state: FSMContext):
    try:
        diff = int(message.text)
        if not (1 <= diff <= 5):
            raise ValueError
    except ValueError:
        diff = 1 # default
    
    await state.update_data(difficulty=diff)
    await message.answer("请输入标签 (用逗号分隔，可选)，或直接回复“无”：")
    await state.set_state(QuizAdminState.waiting_for_tags)

@router.message(QuizAdminState.waiting_for_tags)
async def process_tags(message: Message, state: FSMContext, session: AsyncSession):
    tags_text = message.text
    tags = []
    if tags_text and tags_text != "无":
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]
    
    data = await state.get_data()
    
    # 基础奖励和额外奖励根据难度自动计算
    difficulty = data['difficulty']
    base_reward = 5 * difficulty
    bonus_reward = 15 * difficulty
    
    quiz = QuizQuestionModel(
        question=data['question'],
        options=data['options'],
        correct_index=data['correct_index'],
        difficulty=difficulty,
        reward_base=base_reward,
        reward_bonus=bonus_reward,
        tags=tags,
        is_active=True
    )
    
    session.add(quiz)
    await session.commit()
    
    await state.clear()
    await message.answer(f"✅ 题目已添加！(ID: {quiz.id})\n\n{data['question']}")

# --- 图片管理 ---

@router.message(Command("add_quiz_image"))
async def cmd_add_quiz_image(message: Message, state: FSMContext):
    """添加题目图片"""
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.answer("⚠️ 请回复一张图片使用此命令。")
        return
        
    photo = message.reply_to_message.photo[-1]
    await state.update_data(file_id=photo.file_id, file_unique_id=photo.file_unique_id)
    
    await message.answer("请输入图片标签 (用逗号分隔)，用于关联题目：")
    await state.set_state(QuizAdminState.waiting_for_image_tags)

@router.message(QuizAdminState.waiting_for_image_tags)
async def process_image_tags(message: Message, state: FSMContext, session: AsyncSession):
    tags_text = message.text
    tags = [t.strip() for t in tags_text.split(",") if t.strip()]
    
    if not tags:
        await message.answer("⚠️ 必须指定至少一个标签。")
        return
        
    data = await state.get_data()
    
    img = QuizImageModel(
        file_id=data['file_id'],
        file_unique_id=data['file_unique_id'],
        tags=tags,
        is_active=True,
        description=f"Uploaded by {message.from_user.id}"
    )
    
    session.add(img)
    await session.commit()
    
    await state.clear()
    await message.answer(f"✅ 图片已添加！(ID: {img.id})\n标签: {tags}")
