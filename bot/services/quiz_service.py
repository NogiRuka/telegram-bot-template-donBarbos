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
    KEY_QUIZ_SESSION_TIMEOUT,
    KEY_QUIZ_TRIGGER_PROBABILITY,
)
from bot.database.models import (
    QuizActiveSessionModel,
    QuizImageModel,
    QuizLogModel,
    QuizQuestionModel,
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
            # 这里的任务清理将在外部进行，或者如果这里是 task 的入口函数，
            # 我们应该在完成时从集合中移除自己吗？
            # 实际上，create_task 的调用者应该负责添加到集合，
            # 而这里可以用回调移除，或者在这里移除。
            # 为了简单，我们在调用处处理集合管理。
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
        last_log_stmt = select(QuizLogModel.created_at).where(
            QuizLogModel.user_id == user_id
        ).order_by(desc(QuizLogModel.created_at)).limit(1)
        last_time = (await session.execute(last_log_stmt)).scalar()

        if last_time:
            # 计算时间差
            elapsed = now() - last_time
            if elapsed < timedelta(minutes=cooldown_min):
                return False

        return True

    @classmethod
    async def get_random_image_by_tags(cls, session: AsyncSession, tags: list[str]) -> QuizImageModel | None:
        """根据标签随机获取图片

        功能说明:
        - 在所有启用图片中筛选与标签有交集的图片，并随机返回一张

        输入参数:
        - session: 数据库会话
        - tags: 标签列表

        返回值:
        - Optional[QuizImageModel]: 随机匹配的图片或 None
        """
        if not tags:
            return None

        img_stmt = select(QuizImageModel).where(QuizImageModel.is_active)
        imgs = (await session.execute(img_stmt)).scalars().all()

        matched_imgs = [
            img for img in imgs
            if img.tags and set(tags) & set(img.tags)
        ]

        if matched_imgs:
            return random.choice(matched_imgs)
        return None

    @staticmethod
    async def build_quiz_caption(
        question: QuizQuestionModel,
        image: QuizImageModel | None,
        session: AsyncSession = None,
        timeout_sec: int | None = None,
        title: str = "桜之问答",
    ) -> str:
        """
        构建问答消息说明

        功能说明:
        - 根据题目与图片信息生成统一的 HTML 样式说明文本
        - 包含分类名称、超时提示、图片来源与补充说明（当来源为链接时，优先使用 extra_caption 作为链接文字）

        输入参数:
        - question: 题目对象
        - image: 图片对象（可选）
        - session: 数据库会话（可选，若未提供 timeout_sec 则必须提供）
        - timeout_sec: 会话超时时间（秒，可选，若未提供则从数据库获取）
        - title: 标题（默认桜之问答，可自定义，如测试标题）

        返回值:
        - str: 构建完成的说明文本（HTML）
        """
        if timeout_sec is None:
            if session:
                timeout_sec = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
            else:
                timeout_sec = 60 # 默认值，防止 session 和 timeout_sec 都没传的情况

        if image and image.image_source:
            if image.image_source.startswith("http"):
                link_text = image.extra_caption.strip() if image.extra_caption else "链接"
                extra = f"<a href='{image.image_source}'>{link_text}</a>"
            else:
                extra = f"{image.image_source}"

        cat_name = question.category.name if question.category else "无分类"

        return (
            f"🫧 <b>{title}｜{timeout_sec} 秒挑战 🫧</b>\n\n"
            f"🗂️ {cat_name}｜🖼️ {extra}\n\n"
            f"💭 {question.question}"
        )


    @staticmethod
    async def create_quiz_session(session: AsyncSession, user_id: int, chat_id: int) -> tuple[QuizQuestionModel, QuizImageModel | None, InlineKeyboardMarkup, int] | None:
        """
        创建问答会话

        :param session: 数据库会话
        :param user_id: 用户ID
        :param chat_id: 聊天ID
        :return: (Question, Image, Keyboard, SessionID) or None
        """
        # 若已有活跃会话，直接返回 None 或清理过期
        active_stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.user_id == user_id)
        active_session = (await session.execute(active_stmt)).scalar_one_or_none()
        if active_session:
            if active_session.expire_at <= now():
                await QuizService.handle_timeout(session, user_id)
            else:
                return None

        # 获取超时时间配置
        timeout_sec = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
        # 1. 随机选取题目
        # 这种写法在数据量大时效率较低，但对于初期足够
        stmt = select(QuizQuestionModel).where(QuizQuestionModel.is_active).order_by(func.random()).limit(1)
        question = (await session.execute(stmt)).scalar_one_or_none()

        if not question:
            return None

        # 2. 随机选取图片 (如果题目有 tag)
        quiz_image = await QuizService.get_random_image_by_tags(session, question.tags)

        # 3. 构建选项键盘（保持输入顺序）
        options = question.options  # list[str]
        correct_index = question.correct_index

        # 创建索引列表（不打乱，保持用户输入顺序）
        indices = list(range(len(options)))

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
        builder.adjust(2)  # 每行2个（示例：第一行 A B；第二行 C D）

        # 4. 创建 Session
        expire_at = compute_expire_at(now(), timeout_sec)

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
        try:
            await session.commit()
            await session.refresh(quiz_session)
        except IntegrityError:
            await session.rollback()
            logger.warning("重复的活跃会话，跳过创建")
            return None

        return question, quiz_image, builder.as_markup(), quiz_session.id

    @staticmethod
    async def update_session_message_id(session: AsyncSession, session_id: int, message_id: int) -> None:
        """更新 Session 的 Message ID"""
        stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.id == session_id)
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()
        if quiz_session:
            quiz_session.message_id = message_id
            await session.commit()

    @staticmethod
    async def handle_answer(session: AsyncSession, user_id: int, answer_index: int) -> tuple[bool, int, str]:
        """
        处理用户回答
        :return: (is_correct, reward_amount, message_text)
        """
        # 1. 获取 Session
        stmt = select(QuizActiveSessionModel).where(QuizActiveSessionModel.user_id == user_id)
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()

        if not quiz_session:
            return False, 0, "⚠️ 题目已过期或不存在。"

        # 检查是否过期
        if quiz_session.expire_at <= now():
            chat_id = quiz_session.chat_id
            message_id = quiz_session.message_id
            await QuizService.handle_timeout(session, user_id)
            msg = "⚠️ 题目已过期或不存在。"
            raise QuizSessionExpiredError(msg, chat_id=chat_id, message_id=message_id)

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

        if is_correct:
            msg = "✅ 回答正确！"  # noqa: RUF001
        else:
            correct_option = question.options[question.correct_index]
            msg = f"❌ 回答错误。\n正确答案是：{correct_option}"  # noqa: RUF001
        msg += f"\n获得奖励：+{reward} 精粹"  # noqa: RUF001

        return is_correct, reward, msg

    @staticmethod
    async def handle_timeout(session: AsyncSession, user_id: int) -> None:
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
