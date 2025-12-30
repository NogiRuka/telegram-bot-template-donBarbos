import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import (
    QuizQuestionModel,
    QuizImageModel,
    QuizActiveSessionModel,
    QuizLogModel,
)
from bot.services.currency import CurrencyService
from bot.utils.datetime import now


class QuizService:
    # 配置常量 (可后续改为从 ConfigService 获取)
    COOLDOWN_MINUTES = 10
    TRIGGER_PROBABILITY = 0.05  # 5%
    DAILY_LIMIT = 10
    SESSION_TIMEOUT_SECONDS = 30
    
    @staticmethod
    async def check_trigger_conditions(session: AsyncSession, user_id: int, chat_id: int) -> bool:
        """
        检查是否满足触发问答的条件
        
        :param session: 数据库会话
        :param user_id: 用户ID
        :param chat_id: 聊天ID (用于区分群组/私聊，目前逻辑通用)
        :return: True if triggered, False otherwise
        """
        # 1. 检查是否存在活跃会话
        active_stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.user_id == user_id)
        active_result = await session.execute(active_stmt)
        active_session = active_result.scalar_one_or_none()
        
        if active_session:
            # 检查是否过期
            if active_session.expire_at < int(now().timestamp()):
                # 过期处理：记录日志并删除
                await QuizService.handle_timeout(session, user_id)
                # 继续后续流程（视为无活跃会话）
            else:
                # 还有效，不触发新题目
                return False

        # 2. 概率检查 (最先检查，减少DB查询)
        if random.random() > QuizService.TRIGGER_PROBABILITY:
            return False

        # 3. 每日次数检查
        today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count_stmt = select(func.count(QuizLogModel.id)).where(
            and_(
                QuizLogModel.user_id == user_id,
                QuizLogModel.created_at >= today_start
            )
        )
        daily_count = (await session.execute(daily_count_stmt)).scalar() or 0
        if daily_count >= QuizService.DAILY_LIMIT:
            return False

        # 4. 冷却时间检查
        last_log_stmt = select(QuizLogModel.created_at).where(
            QuizLogModel.user_id == user_id
        ).order_by(desc(QuizLogModel.created_at)).limit(1)
        last_time = (await session.execute(last_log_stmt)).scalar()
        
        if last_time:
            # 这里的 last_time 是带时区的 datetime (TimestampMixin 默认 utcnow)
            # 假设 bot.utils.datetime.now() 返回带时区的时间
            # 需要确保时间比较的兼容性
            if last_time.tzinfo is None:
                # 如果数据库存的是 naive UTC
                pass 
            
            # 计算时间差
            elapsed = now() - last_time
            if elapsed < timedelta(minutes=QuizService.COOLDOWN_MINUTES):
                return False

        return True

    @staticmethod
    async def create_quiz_session(session: AsyncSession, user_id: int, chat_id: int) -> Optional[Tuple[QuizQuestionModel, Optional[QuizImageModel], InlineKeyboardMarkup, int]]:
        """
        创建问答会话
        
        :param session: 数据库会话
        :param user_id: 用户ID
        :param chat_id: 聊天ID
        :return: (Question, Image, Keyboard, SessionID) or None
        """
        # 1. 随机选取题目
        # 这种写法在数据量大时效率较低，但对于初期足够
        stmt = select(QuizQuestionModel).where(QuizQuestionModel.is_active == True).order_by(func.random()).limit(1)
        question = (await session.execute(stmt)).scalar_one_or_none()
        
        if not question:
            return None

        # 2. 随机选取图片 (如果题目有 tag)
        quiz_image = None
        if question.tags:
            # 假设 tags 是 list[str]
            # JSON 数组包含查询 (PostgreSQL @>, SQLite 可能需要 func.json_each)
            # 这里简化处理：直接查找 active 的图片，然后在内存中过滤 tag 匹配的 (数据量不大时)
            # 或者，如果 tags 存储简单，可以用 LIKE。
            # 为了严谨，我们先查出所有 active 图片，再筛选。
            # 优化：数据库层面随机筛选一张匹配的。
            # 由于 SQLDialect 差异，这里用 Python 筛选。
            
            img_stmt = select(QuizImageModel).where(QuizImageModel.is_active == True)
            imgs = (await session.execute(img_stmt)).scalars().all()
            
            # 筛选有交集的图片
            matched_imgs = [
                img for img in imgs 
                if img.tags and set(question.tags) & set(img.tags)
            ]
            
            if matched_imgs:
                quiz_image = random.choice(matched_imgs)

        # 3. 构建选项键盘 (打乱顺序)
        options = question.options  # list[str]
        correct_index = question.correct_index
        
        # 创建索引列表并打乱
        indices = list(range(len(options)))
        random.shuffle(indices)
        
        # 找到新的正确答案索引（实际上 Session 存的是原始索引，回调传回的也是原始索引，所以显示顺序变了不影响逻辑）
        # 等等，如果在 Session 中存原始 correct_index，那么回调时只要传回用户选的原始索引即可。
        # 按钮 callback_data: quiz:answer:{option_index}
        # 这里的 option_index 指的是 options 列表中的下标。
        # 无论按钮怎么排，这个下标指向的内容不变。
        
        builder = InlineKeyboardBuilder()
        for idx in indices:
            builder.button(
                text=options[idx],
                callback_data=f"quiz:ans:{idx}" 
            )
        builder.adjust(2) # 每行2个

        # 4. 创建 Session
        expire_at = int((now() + timedelta(seconds=QuizService.SESSION_TIMEOUT_SECONDS)).timestamp())
        
        # 这里的 message_id 暂时填 0，发送消息后需要更新
        quiz_session = QuizActiveSessionModel(
            user_id=user_id,
            chat_id=chat_id,
            message_id=0, 
            question_id=question.id,
            correct_index=correct_index,
            expire_at=expire_at
        )
        session.add(quiz_session)
        await session.commit()
        await session.refresh(quiz_session)
        
        return question, quiz_image, builder.as_markup(), quiz_session.id

    @staticmethod
    async def update_session_message_id(session: AsyncSession, session_id: int, message_id: int):
        """更新 Session 的 Message ID"""
        stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.id == session_id)
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()
        if quiz_session:
            quiz_session.message_id = message_id
            await session.commit()

    @staticmethod
    async def handle_answer(session: AsyncSession, user_id: int, answer_index: int) -> Tuple[bool, int, str]:
        """
        处理用户回答
        
        :return: (is_correct, reward_amount, message_text)
        """
        # 1. 获取 Session
        stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.user_id == user_id)
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()
        
        if not quiz_session:
            return False, 0, "⚠️ 题目已过期或不存在。"

        # 2. 获取题目信息 (计算奖励)
        question = await session.get(QuizQuestionModel, quiz_session.question_id)
        if not question:
            # 异常情况，清理 session
            await session.delete(quiz_session)
            await session.commit()
            return False, 0, "⚠️ 题目数据异常。"

        # 3. 判定结果
        is_correct = (answer_index == quiz_session.correct_index)
        
        # 4. 计算奖励
        reward = question.reward_bonus if is_correct else question.reward_base
        
        # 5. 记录日志
        log = QuizLogModel(
            user_id=user_id,
            chat_id=quiz_session.chat_id,
            question_id=quiz_session.question_id,
            user_answer=answer_index,
            is_correct=is_correct,
            reward_amount=reward,
            # time_taken 暂未精确计算，可用 now() 减去 session 创建时间估算，但 session 没有 created_at 字段(只有mixin的)
            # 这里简单处理
            time_taken=None 
        )
        session.add(log)
        
        # 6. 发放奖励
        if reward > 0:
            await CurrencyService.add_currency(
                session, 
                user_id, 
                reward, 
                "quiz_reward", 
                f"问答奖励: {'答对' if is_correct else '答错'}"
            )

        # 7. 删除 Session
        await session.delete(quiz_session)
        await session.commit()
        
        msg = "✅ 回答正确！" if is_correct else f"❌ 回答错误。\n正确答案是：{question.options[question.correct_index]}"
        msg += f"\n获得奖励：+{reward} 精粹"
        
        return is_correct, reward, msg

    @staticmethod
    async def handle_timeout(session: AsyncSession, user_id: int):
        """
        处理超时 (通常由定时任务调用，或者用户点击已过期的按钮时触发清理)
        """
        stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.user_id == user_id)
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()
        
        if quiz_session:
            # 记录超时日志
            log = QuizLogModel(
                user_id=user_id,
                chat_id=quiz_session.chat_id,
                question_id=quiz_session.question_id,
                user_answer=None, # NULL 表示未答/超时
                is_correct=False,
                reward_amount=0,
                time_taken=None
            )
            session.add(log)
            await session.delete(quiz_session)
            await session.commit()
