import asyncio
import random
from datetime import timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import (
    KEY_QUIZ_COOLDOWN_MINUTES,
    KEY_QUIZ_DAILY_LIMIT,
    KEY_QUIZ_GLOBAL_ENABLE,
    KEY_QUIZ_SCHEDULE_TARGET_COUNT,
    KEY_QUIZ_SCHEDULE_TARGET_TYPE,
    KEY_QUIZ_SESSION_TIMEOUT,
    KEY_QUIZ_TRIGGER_PROBABILITY,
)
from bot.database.models import (
    QuizActiveSessionModel,
    QuizImageModel,
    QuizLogModel,
    QuizQuestionModel,
    UserModel,
)
from bot.services.config_service import get_config
from bot.services.currency import CurrencyService
from bot.utils.datetime import compute_expire_at, now
from bot.utils.message import safe_delete_message


class QuizSessionExpiredError(Exception):
    """问答会话已过期异常"""
    def __init__(self, message: str = "题目已过期", chat_id: int = 0, message_id: int = 0) -> None:
        self.message = message
        self.chat_id = chat_id
        self.message_id = message_id
        super().__init__(self.message)


class QuizService:
    # 用于保存后台任务的引用，防止被垃圾回收
    _background_tasks = set()

    @staticmethod
    async def schedule_quiz_timeout(
        bot: Bot,
        chat_id: int,
        message_id: int,
        session_id: int,
        user_id: int,
        timeout: int
    ) -> None:
        """
        调度问答超时处理

        功能说明:
        - 等待指定超时时间
        - 检查 Session 是否仍然存在
        - 若存在则视为超时未答，删除消息并清理 Session
        - 若不存在则视为已回答，不进行操作

        :param bot: Bot 实例
        :param chat_id: 聊天 ID
        :param message_id: 消息 ID
        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :param timeout: 超时秒数
        """
        logger.debug(f"⏳ [问答] 会话 {session_id} 已调度超时处理，将在 {timeout} 秒后执行")

        try:
            # 1. 等待超时
            await asyncio.sleep(timeout)
            logger.debug(f"⏰ [问答] 会话 {session_id} 计时结束，开始检查状态")

            # 2. 检查 Session 状态
            # 需要新的 DB 会话，因为这是一个独立的异步任务
            from bot.database.database import sessionmaker

            async with sessionmaker() as session:
                stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.id == session_id)
                quiz_session = (await session.execute(stmt)).scalar_one_or_none()

                if quiz_session:
                    logger.info(f"⏰ [问答] 会话 {session_id} 已超时。正在删除消息 {message_id}")
                    # Session 还在，说明未回答 -> 超时处理

                    # 删除消息
                    deleted = await safe_delete_message(bot, chat_id, message_id)
                    if not deleted:
                        logger.warning(f"⚠️ [问答] 删除会话 {session_id} 的消息 {message_id} 失败")
                    else:
                        logger.info(f"🗑️ [问答] 会话 {session_id} 的消息 {message_id} 已删除")

                    # 记录日志并清理 Session
                    await QuizService.handle_timeout(session, user_id)
                    # handle_timeout 会 commit
                else:
                    logger.debug(f"✅ [问答] 会话 {session_id} 已处理或已过期，跳过删除")
        except asyncio.CancelledError:
            logger.info(f"🛑 [问答] 会话 {session_id} 的超时任务被取消")
            raise
        except Exception as e:
            logger.error(f"❌ [问答] 会话 {session_id} 超时处理出错: {e}", exc_info=True)
        finally:
            pass

    @classmethod
    def start_timeout_task(
        cls,
        bot: Bot,
        chat_id: int,
        message_id: int,
        session_id: int,
        user_id: int,
        timeout: int
    ) -> None:
        """
        启动超时后台任务（包含 GC 保护）

        :param bot: Bot 实例
        :param chat_id: 聊天 ID
        :param message_id: 消息 ID
        :param session_id: 会话 ID
        :param user_id: 用户 ID
        :param timeout: 超时秒数
        """
        logger.info(f"⏳ [问答] 正在为会话 {session_id} 调度超时处理，时长: {timeout} 秒")
        task = asyncio.create_task(
            cls.schedule_quiz_timeout(
                bot=bot,
                chat_id=chat_id,
                message_id=message_id,
                session_id=session_id,
                user_id=user_id,
                timeout=timeout
            )
        )
        cls._background_tasks.add(task)
        task.add_done_callback(cls._background_tasks.discard)

    @staticmethod
    async def check_trigger_conditions(session: AsyncSession, user_id: int, chat_id: int, bot: Bot | None = None) -> bool:
        """
        检查是否满足触发问答的条件

        :param session: 数据库会话
        :param user_id: 用户ID
        :param chat_id: 聊天ID (用于区分群组/私聊，目前逻辑通用)
        :param bot: Bot实例 (用于删除过期消息)
        :return: True if triggered, False otherwise
        """
        # 0. 检查总开关
        global_enabled = await get_config(session, KEY_QUIZ_GLOBAL_ENABLE)
        if global_enabled is False: # None 默认开启
            return False

        # 获取配置
        trigger_prob = await get_config(session, KEY_QUIZ_TRIGGER_PROBABILITY)
        daily_limit = await get_config(session, KEY_QUIZ_DAILY_LIMIT)
        cooldown_min = await get_config(session, KEY_QUIZ_COOLDOWN_MINUTES)

        # 1. 检查是否存在活跃会话
        active_stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.user_id == user_id)
        active_result = await session.execute(active_stmt)
        active_session = active_result.scalar_one_or_none()

        if active_session:
            # 检查是否过期（expire_at 采用 datetime，精确到秒）
            if active_session.expire_at <= now():
                # 如果传入了 bot 且有消息 ID，尝试删除过期消息
                if bot and active_session.message_id and active_session.message_id > 0:
                    try:
                        await bot.delete_message(active_session.chat_id, active_session.message_id)
                    except Exception as e:
                        logger.warning(f"删除过期问答消息失败: {e}")

                # 过期处理：记录日志并删除
                await QuizService.handle_timeout(session, user_id)
                # 继续后续流程（视为无活跃会话）
            else:
                # 还有效，不触发新题目
                return False

        # 2. 概率检查 (最先检查，减少DB查询)
        if random.random() > trigger_prob:
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
        if daily_count >= daily_limit:
            return False

        # 4. 冷却时间检查
        last_log_stmt = select(QuizLogModel).where(
            QuizLogModel.user_id == user_id
        ).order_by(QuizLogModel.created_at.desc()).limit(1)
        last_log = (await session.execute(last_log_stmt)).scalar_one_or_none()

        if last_log:
            next_allowed = last_log.created_at + timedelta(minutes=cooldown_min)
            if now() < next_allowed:
                return False

        return True

    @staticmethod
    async def create_quiz_session(session: AsyncSession, user_id: int, chat_id: int) -> tuple[QuizQuestionModel, QuizImageModel | None, InlineKeyboardMarkup, int] | None:
        """
        创建新的问答会话
        """
        # 1. 随机选择题目 (可优化为加权随机)
        # 获取所有启用的题目ID
        q_ids = (await session.execute(select(QuizQuestionModel.id).where(QuizQuestionModel.is_active == True))).scalars().all()
        if not q_ids:
            return None
        
        q_id = random.choice(q_ids)
        question = await session.get(QuizQuestionModel, q_id)
        if not question:
            return None

        # 2. 随机选择图片 (可选)
        # 50% 概率带图，或者根据题目是否有特定配置
        # 这里简单处理：如果题目有分类，优先选同分类图片；否则随机。
        image = None
        if random.random() < 0.5:
            img_stmt = select(QuizImageModel).where(QuizImageModel.is_active == True)
            if question.category_id:
                img_stmt = img_stmt.where(QuizImageModel.category_id == question.category_id)
            
            # 随机取一张
            # SQLite RANDOM() func.random()
            img_stmt = img_stmt.order_by(func.random()).limit(1)
            image = (await session.execute(img_stmt)).scalar_one_or_none()

        # 3. 创建会话记录
        # 打乱选项
        options = list(question.options)
        correct_option = options[question.correct_index]
        random.shuffle(options)
        new_correct_index = options.index(correct_option)

        # 计算过期时间
        timeout_sec = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
        if timeout_sec is None:
            timeout_sec = 60 # 默认60秒
        expire_at = compute_expire_at(timeout_sec)

        quiz_session = QuizActiveSessionModel(
            user_id=user_id,
            chat_id=chat_id,
            message_id=0, # 稍后更新
            question_id=question.id,
            correct_index=new_correct_index,
            expire_at=expire_at,
            extra={"shuffled_options": options}
        )
        session.add(quiz_session)
        await session.commit()
        await session.refresh(quiz_session)

        # 4. 构建键盘
        markup = QuizService.build_quiz_keyboard(options, quiz_session.id)

        return question, image, markup, quiz_session.id

    @staticmethod
    def build_quiz_keyboard(options: list[str], session_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for i, opt in enumerate(options):
            builder.button(text=opt, callback_data=f"quiz:ans:{session_id}:{i}")
        builder.adjust(1) # 每行一个
        return builder.as_markup()

    @staticmethod
    async def build_quiz_caption(question: QuizQuestionModel, image: QuizImageModel | None, session: AsyncSession) -> str:
        """构建题目文案"""
        # 获取奖励配置
        base = question.reward_base
        bonus = question.reward_bonus
        
        currency_name = await CurrencyService.get_currency_name(session)
        
        text = (
            f"🎲 *趣味问答* 🎲\n\n"
            f"❓ *问题*: {question.question}\n"
        )
        if question.difficulty > 1:
            text += f"🔥 难度: {'⭐' * question.difficulty}\n"
            
        text += f"\n💰 *奖励*:\n"
        text += f"• 答对: +{base + bonus} {currency_name}\n"
        text += f"• 答错: +{base} {currency_name} (低保)\n"
        
        if image and image.description:
            text += f"\n🖼️ *提示*: {image.description}\n"
            
        text += "\n⏳ 请在倒计时结束前作答！"
        return text

    @staticmethod
    async def update_session_message_id(session: AsyncSession, session_id: int, message_id: int) -> None:
        """更新会话的消息ID"""
        stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.id == session_id)
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()
        if quiz_session:
            quiz_session.message_id = message_id
            await session.commit()

    @staticmethod
    async def handle_answer(session: AsyncSession, session_id: int, user_index: int, user_id: int) -> dict:
        """
        处理用户回答
        :return: 结果字典 {is_correct, reward, correct_option, user_option}
        """
        # 1. 获取会话
        stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.id == session_id)
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()
        
        if not quiz_session:
            raise QuizSessionExpiredError("会话已过期或不存在")
            
        if quiz_session.user_id != user_id:
            raise ValueError("这不是你的题目哦")

        # 2. 验证答案
        is_correct = (user_index == quiz_session.correct_index)
        
        # 获取题目信息
        question = await session.get(QuizQuestionModel, quiz_session.question_id)
        
        # 3. 发放奖励
        reward = question.reward_base + (question.reward_bonus if is_correct else 0)
        await CurrencyService.add_balance(session, user_id, reward, "quiz_reward", f"问答奖励: Q{question.id}")
        
        # 4. 记录日志
        log = QuizLogModel(
            user_id=user_id,
            chat_id=quiz_session.chat_id,
            question_id=quiz_session.question_id,
            user_answer=user_index,
            is_correct=is_correct
        )
        session.add(log)
        
        # 5. 删除会话
        await session.delete(quiz_session)
        await session.commit()
        
        # 获取选项文本用于显示
        options = quiz_session.extra.get("shuffled_options", [])
        user_opt = options[user_index] if 0 <= user_index < len(options) else "?"
        correct_opt = options[quiz_session.correct_index] if 0 <= quiz_session.correct_index < len(options) else "?"
        
        return {
            "is_correct": is_correct,
            "reward": reward,
            "correct_option": correct_opt,
            "user_option": user_opt,
            "message_id": quiz_session.message_id,
            "chat_id": quiz_session.chat_id
        }

    @staticmethod
    async def handle_timeout(session: AsyncSession, user_id: int) -> None:
        """处理超时（清理会话，不发奖励或发低保? 目前设计是不发）"""
        # 查找该用户的所有过期会话
        stmt = select(QuizActiveSessionModel).where(
            QuizActiveSessionModel.user_id == user_id,
            QuizActiveSessionModel.expire_at <= now()
        )
        sessions = (await session.execute(stmt)).scalars().all()
        
        for s in sessions:
            # 记录日志 (未答)
            log = QuizLogModel(
                user_id=s.user_id,
                chat_id=s.chat_id,
                question_id=s.question_id,
                user_answer=None,
                is_correct=False
            )
            session.add(log)
            await session.delete(s)
            
        await session.commit()

    @staticmethod
    async def trigger_scheduled_quiz(bot: Bot) -> None:
        """
        执行定时问答触发
        """
        from bot.database.database import sessionmaker
        
        logger.info("⏰ [定时问答] 开始执行定时触发任务")

        async with sessionmaker() as session:
            # 1. 再次检查总开关 (双重保障)
            global_enabled = await get_config(session, KEY_QUIZ_GLOBAL_ENABLE)
            if global_enabled is False: # 显式为 False 才跳过，None 默认开启
                 logger.info("⏰ [定时问答] 总开关关闭，任务取消")
                 return

            # 2. 获取目标用户
            target_type = await get_config(session, KEY_QUIZ_SCHEDULE_TARGET_TYPE)
            target_count = await get_config(session, KEY_QUIZ_SCHEDULE_TARGET_COUNT)
            
            users = []
            
            # 基础查询条件：非机器人、未删除
            base_stmt = select(UserModel).where(
                UserModel.is_bot == False,
                UserModel.is_deleted == False
            )

            if target_type == "fixed" and target_count and target_count > 0:
                # 混合模式：一半活跃，一半随机
                half_count = target_count // 2
                rand_count = target_count - half_count
                
                # 活跃用户 (最近更新时间排序)
                active_stmt = base_stmt.order_by(desc(UserModel.updated_at)).limit(half_count)
                active_users = (await session.execute(active_stmt)).scalars().all()
                
                # 随机用户 (排除已选的活跃用户)
                active_ids = [u.id for u in active_users]
                if active_ids:
                    rand_stmt = base_stmt.where(UserModel.id.not_in(active_ids)).order_by(func.random()).limit(rand_count)
                else:
                    rand_stmt = base_stmt.order_by(func.random()).limit(rand_count)
                    
                rand_users = (await session.execute(rand_stmt)).scalars().all()
                
                users = list(active_users) + list(rand_users)
                logger.info(f"⏰ [定时问答] 选中 {len(users)} 名用户 (活跃: {len(active_users)}, 随机: {len(rand_users)})")
            else:
                # 全部用户 (谨慎使用)
                users = (await session.execute(base_stmt)).scalars().all()
                logger.info(f"⏰ [定时问答] 选中全部 {len(users)} 名用户")

            # 3. 发送题目
            count_sent = 0
            for user in users:
                try:
                    # 检查是否有活跃会话，有则跳过
                    active_stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.user_id == user.id)
                    if (await session.execute(active_stmt)).scalar_one_or_none():
                         continue

                    # 创建会话
                    quiz_data = await QuizService.create_quiz_session(session, user.id, user.id) # ChatID = UserID (私聊)
                    if not quiz_data:
                        continue
                        
                    question, image, markup, session_id = quiz_data
                    caption = await QuizService.build_quiz_caption(question, image, session)
                    
                    # 发送消息
                    if image:
                        sent_msg = await bot.send_photo(chat_id=user.id, photo=image.file_id, caption=caption, reply_markup=markup)
                    else:
                        sent_msg = await bot.send_message(chat_id=user.id, text=caption, reply_markup=markup)
                    
                    if sent_msg:
                        await QuizService.update_session_message_id(session, session_id, sent_msg.message_id)
                        
                        # 启动超时任务
                        timeout_sec = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
                        if timeout_sec:
                             QuizService.start_timeout_task(bot, user.id, sent_msg.message_id, session_id, user.id, timeout_sec)
                        
                        count_sent += 1
                        # 避免风控，稍微 sleep 一下? 
                        # await asyncio.sleep(0.1) 
                        
                except Exception as e:
                    logger.warning(f"⏰ [定时问答] 发送给用户 {user.id} 失败: {e}")
            
            logger.info(f"⏰ [定时问答] 任务完成，成功发送 {count_sent} 条")

    @classmethod
    async def start_scheduler(cls, bot: Bot) -> None:
        """启动定时任务调度器"""
        logger.info("⏰ [定时问答] 调度器启动")
        
        from bot.config.constants import KEY_QUIZ_SCHEDULE_ENABLE, KEY_QUIZ_SCHEDULE_TIME
        from bot.database.database import sessionmaker
        from bot.services.config_service import get_config
        
        while True:
            try:
                await asyncio.sleep(1)
                
                # 获取当前时间
                current = now()
                curr_time_str = current.strftime("%H%M%S")
                
                async with sessionmaker() as session:
                    # 检查是否开启
                    enabled = await get_config(session, KEY_QUIZ_SCHEDULE_ENABLE)
                    if enabled is False: # 只有显式 False 才跳过，None 默认开启? 不，默认应该关闭或由上层决定
                        # 之前的代码里 show_schedule_menu: if enabled is None: enabled = False
                        # 这里保持一致，默认 False
                        continue
                    if enabled is None:
                        continue
                        
                    # 检查时间
                    sch_time = await get_config(session, KEY_QUIZ_SCHEDULE_TIME)
                    if sch_time and sch_time == curr_time_str:
                        # 触发!
                        logger.info(f"⏰ [定时问答] 时间匹配 ({sch_time})，触发任务")
                        # 使用 create_task 避免阻塞调度循环
                        # 并稍微延迟一点点避免同一秒多次(其实 sleep(1) 够了)
                        asyncio.create_task(cls.trigger_scheduled_quiz(bot))
                        # 等待一秒确保时间跳变
                        await asyncio.sleep(1)
                        
            except asyncio.CancelledError:
                logger.info("🛑 [定时问答] 调度器已停止")
                break
            except Exception as e:
                logger.error(f"❌ [定时问答] 调度器出错: {e}")
                await asyncio.sleep(5)
