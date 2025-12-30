from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import QuizQuestionModel, QuizImageModel
from bot.keyboards.inline.quiz_admin import quiz_admin_menu_kb, quiz_settings_kb
from bot.services.quiz_config_service import QuizConfigService
from bot.services.quiz_service import QuizService
from bot.states.admin import QuizAdminState
from .router import router

@router.callback_query(F.data == "quiz_admin:menu")
async def show_quiz_menu(callback: CallbackQuery, state: FSMContext):
    """显示问答管理菜单"""
    await state.clear()
    await callback.message.edit_text(
        "🎲 <b>问答管理</b>\n\n请选择操作：",
        reply_markup=quiz_admin_menu_kb()
    )

# --- 快捷添加题目 ---
@router.callback_query(F.data == "quiz_admin:add_quick")
async def start_quick_add(callback: CallbackQuery, state: FSMContext):
    """开始快捷添加"""
    await callback.message.answer(
        "<b>➕ 快捷添加题目</b>\n\n"
        "请发送一张图片（可选），并在 Caption（如果是纯文本则直接发送文本）中按以下格式输入：\n\n"
        "<code>题目描述\n"
        "选项A 选项B 选项C 选项D\n"
        "正确答案序号(1-4)\n"
        "分类(如: 漫画, 小说, 影视, GV)\n"
        "标签(逗号分隔)</code>\n\n"
        "例如：\n"
        "<code>这部番的主角是谁？\n"
        "路人甲 鸣人 佐助 小樱\n"
        "2\n"
        "动漫\n"
        "火影忍者,JUMP</code>",
        parse_mode="HTML"
    )
    await state.set_state(QuizAdminState.waiting_for_quick_add)
    await callback.answer()

@router.message(QuizAdminState.waiting_for_quick_add)
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
        
        # 尝试空格分隔，如果选项里有空格可能出问题，这里假设选项内部无空格，或者使用更复杂的解析
        # 用户输入提示是空格分隔
        options = [o for o in options_text.split(" ") if o]
        if len(options) != 4:
            # 尝试用中文逗号或英文逗号兼容？不，严格按说明空格分隔
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
            difficulty=1, # 默认难度，后续可加逻辑判断
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

# --- 触发设置 ---
@router.callback_query(F.data == "quiz_admin:settings")
async def show_settings(callback: CallbackQuery, session: AsyncSession):
    prob = await QuizConfigService.get_trigger_probability(session)
    cooldown = await QuizConfigService.get_cooldown_minutes(session)
    daily = await QuizConfigService.get_daily_limit(session)
    timeout = await QuizConfigService.get_session_timeout(session)
    
    text = (
        "<b>⚙️ 触发设置</b>\n\n"
        f"🎲 触发概率: {prob:.1%} (每次交互)\n"
        f"⏳ 冷却时间: {cooldown} 分钟\n"
        f"🔢 每日上限: {daily} 次\n"
        f"⏱️ 答题限时: {timeout} 秒"
    )
    await callback.message.edit_text(text, reply_markup=quiz_settings_kb())

# --- 设置修改处理 (简化版: 提示用户输入) ---
@router.callback_query(F.data.startswith("quiz_admin:set:"))
async def ask_setting_value(callback: CallbackQuery, state: FSMContext):
    setting_type = callback.data.split(":")[-1]
    await state.update_data(setting_type=setting_type)
    
    prompts = {
        "probability": "请输入新的触发概率 (0.0 - 1.0)，例如 0.05 表示 5%",
        "cooldown": "请输入新的冷却时间 (分钟，整数)",
        "daily_limit": "请输入新的每日触发上限 (整数)",
        "timeout": "请输入新的答题限时 (秒，整数)"
    }
    
    await callback.message.answer(prompts.get(setting_type, "请输入新值"))
    await state.set_state(QuizAdminState.waiting_for_setting_value)
    await callback.answer()

@router.message(QuizAdminState.waiting_for_setting_value)
async def process_setting_value(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    setting_type = data.get("setting_type")
    value_str = message.text
    
    try:
        if setting_type == "probability":
            val = float(value_str)
            if not (0 <= val <= 1): raise ValueError
            await QuizConfigService.set_trigger_probability(session, val, message.from_user.id)
            
        elif setting_type == "cooldown":
            val = int(value_str)
            await QuizConfigService.set_cooldown_minutes(session, val, message.from_user.id)
            
        elif setting_type == "daily_limit":
            val = int(value_str)
            await QuizConfigService.set_daily_limit(session, val, message.from_user.id)
            
        elif setting_type == "timeout":
            val = int(value_str)
            await QuizConfigService.set_session_timeout(session, val, message.from_user.id)
            
        await message.answer("✅ 设置已更新！")
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ 输入无效，请重试。")

# --- 题目测试 ---
@router.callback_query(F.data == "quiz_admin:test_trigger")
async def test_trigger(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id # 这种情况下是在私聊里，或者管理员在群里点？
    # 如果是在频道/群组面板，chat_id 可能不是私聊。
    # 强制给管理员私聊发送
    target_chat_id = user_id
    
    await callback.answer("正在生成测试题目...")
    
    try:
        # 强制触发，不检查条件
        quiz_data = await QuizService.create_quiz_session(session, user_id, target_chat_id)
        if quiz_data:
            question, image, markup, session_id = quiz_data
            timeout_sec = await QuizConfigService.get_session_timeout(session)
            caption = f"🧪 <b>测试题目</b>\n\n{question.question}\n\n⏳ 限时 {timeout_sec} 秒"
            
            bot = callback.bot
            if image:
                sent = await bot.send_photo(target_chat_id, image.file_id, caption=caption, reply_markup=markup)
            else:
                sent = await bot.send_message(target_chat_id, caption, reply_markup=markup)
                
            await QuizService.update_session_message_id(session, session_id, sent.message_id)
        else:
            await callback.message.answer("⚠️ 题库为空或生成失败。")
            
    except Exception as e:
        await callback.message.answer(f"❌ 测试失败: {e}")

# --- 列表查看 (简易版) ---
@router.callback_query(F.data == "quiz_admin:list_questions")
async def list_questions(callback: CallbackQuery, session: AsyncSession):
    # 只显示最近 10 条
    stmt = select(QuizQuestionModel).order_by(QuizQuestionModel.id.desc()).limit(10)
    questions = (await session.execute(stmt)).scalars().all()
    
    msg = "<b>📋 最近添加的题目 (Top 10):</b>\n\n"
    for q in questions:
        msg += f"ID: {q.id} | {q.category or '无分类'}\nQ: {q.question[:20]}...\n\n"
        
    await callback.message.edit_text(msg, reply_markup=quiz_admin_menu_kb()) # 返回菜单

@router.callback_query(F.data == "quiz_admin:list_images")
async def list_images(callback: CallbackQuery, session: AsyncSession):
    # 只显示最近 10 条
    stmt = select(QuizImageModel).order_by(QuizImageModel.id.desc()).limit(10)
    images = (await session.execute(stmt)).scalars().all()
    
    msg = "<b>🖼️ 最近添加的图片 (Top 10):</b>\n\n"
    for img in images:
        msg += f"ID: {img.id} | {img.category or '无分类'}\nTags: {img.tags}\n\n"
        
    await callback.message.edit_text(msg, reply_markup=quiz_admin_menu_kb())
