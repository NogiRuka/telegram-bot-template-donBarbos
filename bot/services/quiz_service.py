import asyncio
import html
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
from bot.core.constants import CURRENCY_NAME, CURRENCY_SYMBOL
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

    @classmethod
    def _track_task(cls, task: asyncio.Task) -> None:
        cls._background_tasks.add(task)
        task.add_done_callback(cls._background_tasks.discard)

    @classmethod
    async def stop_background_tasks(cls) -> None:
        if not cls._background_tasks:
            return
        tasks = list(cls._background_tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        cls._background_tasks.clear()

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
                stmt = select(QuizActiveSessionModel).where(
                    QuizActiveSessionModel.id == session_id,
                    QuizActiveSessionModel.is_deleted.is_(False),
                )
                # 使用 unique() 防止可能的笛卡尔积（尽管 ID 查询理论上不需要，但防御性编程）
                # 使用 scalars().first() 替代 scalar_one_or_none() 以避免多行错误导致任务崩溃
                quiz_session = (await session.execute(stmt)).unique().scalars().first()

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
        cls._track_task(task)

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
        active_stmt = select(QuizActiveSessionModel).where(
            QuizActiveSessionModel.user_id == user_id,
            QuizActiveSessionModel.is_deleted.is_(False),
        )
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
        logger.info(f"根据标签 {tags} 随机获取图片")
        if not tags:
            return None

        img_stmt = select(QuizImageModel).where(
            QuizImageModel.is_active,
            QuizImageModel.is_deleted.is_(False),
        )
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

        extra = "无"
        # 如果有 extra_caption 则使用它，否则尝试使用第一个标签，最后回退到 "链接"
        link_text = "链接"
        if image and image.extra_caption:
            link_text = image.extra_caption.strip()
        elif image and image.tags and len(image.tags) > 0:
            link_text = image.tags[0]

        if image and image.image_source:
            if image.image_source.startswith("http"):
                # HTML 格式的链接
                extra = f"<a href='{image.image_source}'>{html.escape(link_text)}</a>"
            else:
                extra = f"{html.escape(image.image_source)}"
        else:
            extra = f"{html.escape(link_text)}"

        cat_name = question.category.name if question.category else "无分类"

        return (
            f"🫧 <b>{html.escape(title)}｜{timeout_sec} 秒挑战 🫧</b>\n\n"
            f"🗂️ {html.escape(cat_name)}｜🖼️ {extra}\n\n"
            f"💭 <code>{html.escape(question.question)}</code>"
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
        active_stmt = select(QuizActiveSessionModel).where(
            QuizActiveSessionModel.user_id == user_id,
            QuizActiveSessionModel.is_deleted.is_(False),
        )
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

        # 保存用于重建 caption 的信息
        extra_data = {"timeout_sec": timeout_sec}
        if quiz_image:
            extra_data["image_source"] = quiz_image.image_source
            extra_data["extra_caption"] = quiz_image.extra_caption
            extra_data["tags"] = quiz_image.tags
            extra_data["file_id"] = quiz_image.file_id  # 增加 file_id 记录
            extra_data["image_id"] = quiz_image.id      # 增加 image_id 记录

        # 这里的 message_id 暂时填 0，发送消息后需要更新
        quiz_session = QuizActiveSessionModel(
            user_id=user_id,
            chat_id=chat_id,
            message_id=0,
            question_id=question.id,
            correct_index=correct_index,
            expire_at=expire_at,
            extra=extra_data
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
        """更新会话的消息ID"""
        stmt = select(QuizActiveSessionModel).where(
            QuizActiveSessionModel.id == session_id,
            QuizActiveSessionModel.is_deleted.is_(False),
        )
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()
        if quiz_session:
            quiz_session.message_id = message_id
            await session.commit()

    @staticmethod
    async def handle_answer(session: AsyncSession, user_id: int, answer_index: int) -> tuple[bool, int, str, str]:
        """
        处理用户回答
        :return: (is_correct, reward_amount, message_text, original_caption)
        """
        # 1. 获取 Session
        stmt = select(QuizActiveSessionModel).where(
            QuizActiveSessionModel.user_id == user_id,
            QuizActiveSessionModel.is_deleted.is_(False),
        )
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()

        if not quiz_session:
            return False, 0, "⚠️ 题目已过期或不存在。", ""

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
            quiz_session.is_deleted = True
            quiz_session.deleted_at = now()
            quiz_session.remark = "题目数据异常，自动清理"
            await session.commit()
            return False, 0, "⚠️ 题目数据异常。", ""

        # 重建原始 caption (在删除 session 前进行)
        session_extra = quiz_session.extra or {}
        fake_image = None
        if "image_source" in session_extra:
            fake_image = QuizImageModel(
                image_source=session_extra.get("image_source"),
                extra_caption=session_extra.get("extra_caption"),
                tags=session_extra.get("tags")
            )

        original_caption = await QuizService.build_quiz_caption(
            question=question,
            image=fake_image,
            session=session,
            timeout_sec=session_extra.get("timeout_sec")
        )

        # 3. 判定结果
        is_correct = (answer_index == quiz_session.correct_index)

        # 4. 计算奖励
        reward = question.reward_bonus if is_correct else question.reward_base

        # 计算耗时 (秒)
        time_taken = None
        if quiz_session.created_at:
            delta = now() - quiz_session.created_at
            time_taken = int(delta.total_seconds())

        # 5. 记录日志
        log = QuizLogModel(
            user_id=user_id,
            chat_id=quiz_session.chat_id,
            question_id=quiz_session.question_id,
            user_answer=answer_index,
            is_correct=is_correct,
            reward_amount=reward,
            time_taken=time_taken,
            extra=quiz_session.extra  # 保存 extra 数据 (包含图片信息)
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
        quiz_session.is_deleted = True
        quiz_session.deleted_at = now()
        quiz_session.remark = f"用户完成作答: {'答对' if is_correct else '答错'}"
        await session.commit()

        if is_correct:
            msg = "✅ 回答正确！"
        else:
            # correct_option = question.options[question.correct_index]
            msg = "❌ 回答错误。"
            # msg += f"正确答案：{correct_option}"
        msg += f"\n获得{CURRENCY_NAME}：+{reward} {CURRENCY_SYMBOL}"

        return is_correct, reward, msg, original_caption

    @staticmethod
    async def handle_timeout(session: AsyncSession, user_id: int) -> None:
        """
        处理超时 (通常由定时任务调用，或者用户点击已过期的按钮时触发清理)
        """
        stmt = select(QuizActiveSessionModel).where(
            QuizActiveSessionModel.user_id == user_id,
            QuizActiveSessionModel.is_deleted.is_(False),
        )
        quiz_session = (await session.execute(stmt)).scalar_one_or_none()

        if quiz_session:
            # 记录超时日志
            log = QuizLogModel(
                user_id=user_id,
                chat_id=quiz_session.chat_id,
                question_id=quiz_session.question_id,
                user_answer=None, # NULL 表示未答/超时
                is_correct=False,
                extra=quiz_session.extra  # 保存 extra 数据
            )
            session.add(log)
            quiz_session.is_deleted = True
            quiz_session.deleted_at = now()
            quiz_session.remark = "会话超时，自动清理"
        await session.commit()

    @staticmethod
    async def trigger_scheduled_quiz(bot: Bot) -> None:
        """
        执行定时问答触发
        """
        from bot.config.constants import KEY_BOT_FEATURES_ENABLED
        from bot.database.database import sessionmaker
        from bot.database.models import UserExtendModel, UserRole

        logger.info("⏰ [定时问答] 开始执行定时触发任务")

        async with sessionmaker() as session:
            # 1. 再次检查总开关 (双重保障)
            global_enabled = await get_config(session, KEY_QUIZ_GLOBAL_ENABLE)
            if global_enabled is False: # 显式为 False 才跳过，None 默认开启
                 logger.info("⏰ [定时问答] 总开关关闭，任务取消")
                 return

            # 2. 检查机器人功能开关 (KEY_BOT_FEATURES_ENABLED)
            # 如果机器人功能关闭，则只允许 Owner 接收
            bot_enabled = await get_config(session, KEY_BOT_FEATURES_ENABLED)
            # bot_enabled 默认为 True (None 视为开启)
            is_bot_enabled = bot_enabled is not False
            owner_stmt = select(UserExtendModel.user_id).where(UserExtendModel.role == UserRole.owner).limit(1)
            owner_id = (await session.execute(owner_stmt)).scalar_one_or_none()
            if owner_id is None:
                logger.warning("⏰ [定时问答] 未找到所有者(owner)记录，任务取消")
                return

            # 3. 获取目标用户
            target_type = await get_config(session, KEY_QUIZ_SCHEDULE_TARGET_TYPE)
            target_count = await get_config(session, KEY_QUIZ_SCHEDULE_TARGET_COUNT)

            users = []

            # 基础查询条件：非机器人、未删除
            base_stmt = select(UserModel).where(
                UserModel.is_bot.is_(False),
                UserModel.is_deleted.is_(False),
            )

            if not is_bot_enabled:
                logger.info("⏰ [定时问答] 机器人功能已关闭，仅向所有者发送")
                # 仅查询 Owner
                owner_stmt = base_stmt.where(UserModel.id == owner_id)
                users = (await session.execute(owner_stmt)).scalars().all()

            elif target_type == "fixed" and target_count and target_count > 0:
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

            # 4. 发送题目
            count_sent = 0
            for user in users:
                try:
                    # 检查是否有活跃会话，有则跳过
                    active_stmt = select(QuizActiveSessionModel).where(
                        QuizActiveSessionModel.user_id == user.id,
                        QuizActiveSessionModel.is_deleted.is_(False),
                    )
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

        from bot.config.constants import KEY_QUIZ_GLOBAL_ENABLE, KEY_QUIZ_SCHEDULE_ENABLE, KEY_QUIZ_SCHEDULE_TIME
        from bot.database.database import sessionmaker
        from bot.services.config_service import get_config

        while True:
            try:
                await asyncio.sleep(1)

                # 获取当前时间
                current = now()
                curr_time_str = current.strftime("%H%M%S")

                async with sessionmaker() as session:
                    # 检查总开关
                    global_enabled = await get_config(session, KEY_QUIZ_GLOBAL_ENABLE)
                    if global_enabled is False:
                        continue

                    # 检查是否开启
                    enabled = await get_config(session, KEY_QUIZ_SCHEDULE_ENABLE)
                    if enabled is False: # 只有显式 False 才跳过，None 默认开启? 不，默认应该关闭或由上层决定
                        # 之前的代码里 show_schedule_menu: if enabled is None: enabled = False
                        # 这里保持一致，默认 False
                        continue
                    if enabled is None:
                        continue

                    # 检查时间
                    sch_time_str = await get_config(session, KEY_QUIZ_SCHEDULE_TIME)
                    if sch_time_str:
                        # 支持多个时间点，逗号分隔
                        sch_times = [t.strip() for t in sch_time_str.split(",") if t.strip()]
                        if curr_time_str in sch_times:
                            # 触发!
                            logger.info(f"⏰ [定时问答] 时间匹配 ({curr_time_str})，触发任务")
                            cls._track_task(asyncio.create_task(cls.trigger_scheduled_quiz(bot), name="scheduled_quiz"))
                            # 等待一秒确保时间跳变
                            await asyncio.sleep(1)

            except asyncio.CancelledError:
                logger.info("🛑 [定时问答] 调度器已停止")
                break
            except Exception as e:
                logger.error(f"❌ [定时问答] 调度器出错: {e}")
                await asyncio.sleep(5)
