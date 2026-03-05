"""
经济系统服务模块

提供代币查询、签到、交易记录等核心逻辑。
"""

import random
from datetime import timedelta
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import (
    CURRENCY_NAME,
    CURRENCY_SYMBOL,
    PRODUCT_ACTION_CUSTOM_TITLE,
    PRODUCT_ACTION_EMBY_IMAGE,
    PRODUCT_ACTION_EMBY_PASSWORD,
    PRODUCT_ACTION_MAIN_IMAGE_UNLOCK_NSFW,
    PRODUCT_ACTION_RETRO_CHECKIN,
)
from bot.database.models import (
    CurrencyConfigModel,
    CurrencyProductModel,
    CurrencyTransactionModel,
    UserExtendModel,
)
from bot.utils.datetime import now

# CURRENCY_NAME = "精粹"
# CURRENCY_SYMBOL = "💧"


class CurrencyService:
    @staticmethod
    async def get_user_balance(session: AsyncSession, user_id: int) -> int:
        """获取用户当前余额"""
        stmt = select(UserExtendModel.currency_balance).where(UserExtendModel.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def get_user_extend(session: AsyncSession, user_id: int) -> UserExtendModel | None:
        """获取用户扩展信息"""
        stmt = select(UserExtendModel).where(UserExtendModel.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_config(session: AsyncSession, key: str, default: int) -> int:
        """获取动态配置"""
        stmt = select(CurrencyConfigModel.value).where(CurrencyConfigModel.config_key == key)
        result = await session.execute(stmt)
        val = result.scalar()
        return val if val is not None else default

    @staticmethod
    async def daily_checkin(session: AsyncSession, user_id: int) -> tuple[bool, str]:
        """每日签到

        返回: (是否成功, 提示信息)
        """
        try:
            # 1. 获取用户数据
            user_ext = await CurrencyService.get_user_extend(session, user_id)
            if not user_ext:
                # 如果不存在，尝试初始化（通常在用户首次交互时已创建）
                # 这里简单返回失败，提示用户先与机器人交互
                return False, "⚠️ 用户数据不存在，请先发送 /start 与机器人交互。"

            # 2. 检查是否已签到
            today = now().date()
            if user_ext.last_checkin_date == today:
                return False, f"{CURRENCY_SYMBOL} 今日已经签过到了哦！"

            # 3. 读取配置
            base_reward = await CurrencyService.get_config(session, "checkin.base", 10)
            streak_bonus_rate = await CurrencyService.get_config(session, "checkin.streak_bonus_rate", 5)  # 5%
            random_bonus_max = await CurrencyService.get_config(session, "checkin.random_bonus", 5)
            weekly_bonus_val = await CurrencyService.get_config(session, "checkin.weekly_bonus", 20)
            monthly_bonus_val = await CurrencyService.get_config(session, "checkin.monthly_bonus", 50)
            lucky_prob = await CurrencyService.get_config(session, "checkin.lucky_prob", 5)
            lucky_bonus_val = await CurrencyService.get_config(session, "checkin.lucky_bonus", 5)

            # 4. 计算连签
            streak = user_ext.streak_days
            last_date = user_ext.last_checkin_date

            if last_date and (today - last_date).days == 1:
                streak += 1
            else:
                streak = 1

            # 5. 计算奖励
            # 连签加成: bonus = base * min(streak * rate, 1.0)
            streak_bonus_pct = min(streak * (streak_bonus_rate / 100.0), 1.0)
            streak_bonus = int(base_reward * streak_bonus_pct)

            random_val = random.randint(0, random_bonus_max)

            # 额外周期奖励
            weekly_bonus = 0
            monthly_bonus = 0

            # 优先触发月签大礼包 (每30天)
            if streak > 0 and streak % 30 == 0:
                monthly_bonus = monthly_bonus_val
            # 否则触发周签奖励 (每7天)
            elif streak > 0 and streak % 7 == 0:
                weekly_bonus = weekly_bonus_val

            # 幸运暴击
            lucky_bonus = 0
            if random.randint(1, 100) <= lucky_prob:
                lucky_bonus = lucky_bonus_val

            total_reward = base_reward + streak_bonus + random_val + weekly_bonus + monthly_bonus + lucky_bonus

            # 6. 更新数据库
            user_ext.last_checkin_date = today
            user_ext.streak_days = streak
            user_ext.currency_balance += total_reward
            user_ext.currency_total += total_reward

            user_ext.max_streak_days = max(user_ext.max_streak_days, streak)

            # 7. 记录流水
            meta = {
                "base": base_reward,
                "streak_bonus": streak_bonus,
                "random": random_val,
                "streak_days": streak,
            }
            if weekly_bonus > 0:
                meta["weekly_bonus"] = weekly_bonus
            if monthly_bonus > 0:
                meta["monthly_bonus"] = monthly_bonus
            if lucky_bonus > 0:
                meta["lucky_bonus"] = lucky_bonus

            tx = CurrencyTransactionModel(
                user_id=user_id,
                amount=total_reward,
                balance_after=user_ext.currency_balance,
                event_type="daily_checkin",
                description=f"每日签到 (连签 {streak} 天)",
                meta=meta,
            )
            session.add(tx)
            await session.commit()

            # TODO: 运势功能后续添加
            msg_parts = [
                "🎉 签到成功！",
                f"获得：+{total_reward} {CURRENCY_SYMBOL}",
                f"连续：{streak} 天 (加成 +{int(streak_bonus_pct*100)}%)"
            ]

            if weekly_bonus > 0:
                msg_parts.append(f"📈 周签奖励：+{weekly_bonus} {CURRENCY_SYMBOL}")
            if monthly_bonus > 0:
                msg_parts.append(f"🎁 月签大礼包：+{monthly_bonus} {CURRENCY_SYMBOL}")
            if lucky_bonus > 0:
                msg_parts.append(f"🎲 幸运暴击！\n额外获得：{CURRENCY_SYMBOL} +{lucky_bonus}")

            msg_parts.append(f"当前{CURRENCY_NAME}：{user_ext.currency_balance} {CURRENCY_SYMBOL}")

            msg = "\n".join(msg_parts)
            return True, msg

        except Exception as e:
            logger.exception(f"用户 {user_id} 签到失败: {e}")
            return False, "⚠️ 签到服务暂时不可用，请稍后重试。"

    @staticmethod
    async def ensure_configs(session: AsyncSession) -> None:
        """初始化经济系统配置

        如果配置不存在，则使用默认值创建。
        """
        # 默认配置定义: key -> (value, description)
        defaults = {
            "checkin.base": (10, "每日签到基础奖励"),
            "checkin.streak_bonus_rate": (5, "连签加成百分比(%)"),
            "checkin.random_bonus": (5, "随机浮动奖励上限"),
            "checkin.weekly_bonus": (20, "连签7天额外奖励"),
            "checkin.monthly_bonus": (50, "连签30天大礼包"),
            "checkin.lucky_prob": (5, "幸运暴击概率(%)"),
            "checkin.lucky_bonus": (5, "幸运暴击奖励"),
        }

        # 查询现有配置
        stmt = select(CurrencyConfigModel.config_key)
        result = await session.execute(stmt)
        existing_keys = set(result.scalars().all())

        # 插入缺失的配置
        for key, (val, desc) in defaults.items():
            if key not in existing_keys:
                # logger.info(f"初始化经济配置: {key} = {val}")
                config = CurrencyConfigModel(
                    config_key=key,
                    value=val,
                    description=desc
                )
                session.add(config)

        await session.commit()

    @staticmethod
    async def ensure_products(session: AsyncSession) -> None:
        """初始化默认商品"""
        defaults = [
            {
                "name": "补签卡",
                "price": 60,
                "stock": 20,
                "description": "补签昨天的签到记录",
                "category": "tools",
                "action_type": PRODUCT_ACTION_RETRO_CHECKIN,
            },
            {
                "name": "修改头像",
                "price": 60,
                "stock": 20,
                "description": "修改 Emby 账号头像 (一次性)",
                "category": "emby",
                "action_type": PRODUCT_ACTION_EMBY_IMAGE,
                "purchase_conditions": {"has_emby": True},
            },
            {
                "name": "修改密码",
                "price": 60,
                "stock": 20,
                "description": "修改 Emby 账号密码 (一次性)",
                "category": "emby",
                "action_type": PRODUCT_ACTION_EMBY_PASSWORD,
                "purchase_conditions": {"has_emby": True},
            },
            {
                "name": "自定义头衔（7天）",
                "price": 100,
                "stock": 20,
                "description": "在群组中显示自定义头衔（7天体验）。",
                "category": "tools",
                "action_type": PRODUCT_ACTION_CUSTOM_TITLE,
            },
            {
                "name": "自定义头衔（永久）",
                "price": 1000,
                "stock": 10,
                "description": "在群组中显示自定义头衔（永久）。\n🎉 恭喜您连续签到30天解锁此隐藏商品！",
                "category": "tools",
                "action_type": PRODUCT_ACTION_CUSTOM_TITLE,
                "visible_conditions": {"min_max_streak": 30},
            },
            {
                "name": "解锁🔞主图",
                "price": 60,
                "stock": 20,
                "description": "解锁主图的 NSFW/随机展示模式设置权限",
                "category": "tools",
                "action_type": PRODUCT_ACTION_MAIN_IMAGE_UNLOCK_NSFW,
            },
        ]

        for product in defaults:
            exists = await session.scalar(
                select(CurrencyProductModel.id)
                .where(CurrencyProductModel.name == product["name"])
                .limit(1)
            )
            if exists:
                continue

            data = product.copy()
            await CurrencyService.create_product(
                session=session,
                is_active=True,
                **data
            )

    @staticmethod
    async def add_currency(
        session: AsyncSession,
        user_id: int,
        amount: int,
        event_type: str,
        description: str,
        meta: dict[str, Any] | None = None,
        is_consumed: bool = True,
        commit: bool = True,
    ) -> int:
        """增加/扣除代币

        输入参数:
        - user_id: 用户ID
        - amount: 变动数值 (正数增加，负数扣除)
        - event_type: 事件类型
        - description: 描述
        - meta: 扩展信息
        - is_consumed: 是否已消耗 (False 表示购买了资格但未使用)
        - commit: 是否提交事务 (默认为 True)

        返回值:
        - int: 变动后的余额
        """
        user_ext = await CurrencyService.get_user_extend(session, user_id)
        if not user_ext:
            logger.warning(f"⚠️ 尝试给不存在的用户 {user_id} 变更代币")
            return 0

        # 检查余额是否足够 (如果是扣除)
        if amount < 0 and user_ext.currency_balance + amount < 0:
            msg = "💸 余额不足"
            raise ValueError(msg)

        user_ext.currency_balance += amount
        if amount > 0:
            user_ext.currency_total += amount

        tx = CurrencyTransactionModel(
            user_id=user_id,
            amount=amount,
            balance_after=user_ext.currency_balance,
            event_type=event_type,
            description=description,
            meta=meta,
            is_consumed=is_consumed,
        )
        session.add(tx)

        if commit:
            await session.commit()

        return user_ext.currency_balance

    @staticmethod
    async def create_product(
        session: AsyncSession,
        name: str,
        price: int,
        stock: int,
        description: str,
        category: str,
        action_type: str,
        purchase_conditions: dict[str, Any] | None = None,
        visible_conditions: dict[str, Any] | None = None,
        is_active: bool = False,
    ) -> CurrencyProductModel:
        """创建新商品"""
        product = CurrencyProductModel(
            name=name,
            price=price,
            stock=stock,
            description=description,
            category=category,
            action_type=action_type,
            purchase_conditions=purchase_conditions,
            visible_conditions=visible_conditions,
            is_active=is_active,
        )
        session.add(product)
        await session.commit()
        return product

    @staticmethod
    async def get_products(session: AsyncSession, user_id: int | None = None, only_active: bool = True) -> list[CurrencyProductModel]:
        """获取商品列表

        参数:
        - session: 数据库会话
        - user_id: 用户ID (可选, 用于可见性检查)
        - only_active: 仅获取上架商品
        """
        stmt = select(CurrencyProductModel)
        if only_active:
            stmt = stmt.where(CurrencyProductModel.is_active.is_(True))

        stmt = stmt.order_by(CurrencyProductModel.price)
        result = await session.execute(stmt)
        products = list(result.scalars().all())

        if user_id is None:
            return products

        # 可见性检查
        visible_products = []
        user_ext = await CurrencyService.get_user_extend(session, user_id)

        for product in products:
            if not product.visible_conditions:
                visible_products.append(product)
                continue

            conditions = product.visible_conditions

            # 检查条件: min_max_streak (最小历史最高连签天数)
            if "min_max_streak" in conditions:
                min_streak = conditions["min_max_streak"]
                if not user_ext or user_ext.max_streak_days < min_streak:
                    continue

            visible_products.append(product)

        return visible_products

    @staticmethod
    async def update_product(
        session: AsyncSession,
        product_id: int,
        **kwargs
    ) -> CurrencyProductModel | None:
        """更新商品信息

        支持更新的字段: description, price, stock, is_active
        """
        product = await CurrencyService.get_product(session, product_id)
        if not product:
            return None

        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)

        session.add(product)
        await session.commit()
        return product

    @staticmethod
    async def get_product(session: AsyncSession, product_id: int) -> CurrencyProductModel | None:
        """获取单个商品"""
        stmt = select(CurrencyProductModel).where(CurrencyProductModel.id == product_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_product_by_action(session: AsyncSession, action_type: str) -> CurrencyProductModel | None:
        """根据行为类型获取商品"""
        stmt = select(CurrencyProductModel).where(
            CurrencyProductModel.action_type == action_type,
            CurrencyProductModel.is_active.is_(True)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_purchase_history(session: AsyncSession, limit: int = 10, offset: int = 0) -> list[CurrencyTransactionModel]:
        """获取购买记录"""
        stmt = select(CurrencyTransactionModel).where(
            CurrencyTransactionModel.event_type == "purchase"
        ).order_by(CurrencyTransactionModel.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def purchase_product(session: AsyncSession, user_id: int, product_id: int) -> tuple[bool, str]:
        """购买商品

        返回: (是否成功, 提示信息)
        """
        # 1. 获取商品
        product = await CurrencyService.get_product(session, product_id)

        if not product:
            return False, "❌ 商品不存在"

        if not product.is_active:
            return False, "🚫 商品已下架"

        if product.stock != -1 and product.stock <= 0:
            return False, "📦 商品库存不足"

        # 1.5 检查购买条件
        if product.purchase_conditions:
            conditions = product.purchase_conditions
            user_ext = await CurrencyService.get_user_extend(session, user_id)

            # 检查条件: has_emby (拥有 Emby 账号)
            if conditions.get("has_emby") and (not user_ext or not user_ext.emby_user_id):
                return False, "🚫 您未绑定 Emby 账号，无法购买此商品。"

        # 判断是否为功能性商品（购买资格券）
        is_ticket = product.action_type in [PRODUCT_ACTION_EMBY_IMAGE, PRODUCT_ACTION_EMBY_PASSWORD]

        # 2. 扣除代币
        try:
            await CurrencyService.add_currency(
                session,
                user_id,
                -product.price,
                "purchase",
                f"购买 {product.name}",
                meta={"product_id": product.id, "product_name": product.name, "action_type": product.action_type},
                is_consumed=not is_ticket,  # 如果是票据，标记为未消耗
                commit=False  # 不立即提交，等待后续逻辑确认
            )
        except ValueError:
            return False, f"💸 余额不足，需要 {product.price} {CURRENCY_SYMBOL}"

        # 3. 扣减库存 (如果是有限库存)
        if product.stock != -1:
            product.stock -= 1
            session.add(product)

        # 4. 执行商品效果
        success, effect_msg = await CurrencyService._handle_product_effect(session, user_id, product)

        if not success:
            await session.rollback()
            return False, effect_msg

        await session.commit()

        return True, f"🛍️ 购买成功！消耗 {product.price} {CURRENCY_SYMBOL}\n{effect_msg}"

    @staticmethod
    async def _handle_product_effect(session: AsyncSession, user_id: int, product: CurrencyProductModel) -> tuple[bool, str]:
        """处理商品生效逻辑

        返回: (是否成功, 提示信息)
        """
        try:
            if product.action_type == PRODUCT_ACTION_RETRO_CHECKIN:
                # 尝试补签逻辑
                return await CurrencyService._try_retro_checkin(session, user_id)

            if product.action_type in [PRODUCT_ACTION_EMBY_IMAGE, PRODUCT_ACTION_EMBY_PASSWORD]:
                # 功能性商品，购买后获得资格
                return True, "✅ 您已获得使用资格，请前往 [账号中心] 使用对应功能。"

            if product.action_type == PRODUCT_ACTION_MAIN_IMAGE_UNLOCK_NSFW:
                # 解锁主图 NSFW/随机设置权限（幂等）
                ext = await CurrencyService.get_user_extend(session, user_id)
                if not ext:
                    return False, "⚠️ 用户数据不存在。"
                ext.nsfw_unlocked = True
                session.add(ext)
                return True, "✅ 已解锁主图 NSFW/随机模式设置。"

            if product.action_type == PRODUCT_ACTION_CUSTOM_TITLE:
                return True, "ℹ️ 请联系频道管理员设置您的自定义群组头衔。"

            # 默认回复
            return True, "✅ 商品购买成功。请联系频道处理。"
        except Exception as e:
            logger.exception(f"商品 {product.id} 效果执行失败: {e}")
            return False, "⚠️ 商品效果执行出现异常，请联系管理员。"

    @staticmethod
    async def _try_retro_checkin(session: AsyncSession, user_id: int) -> tuple[bool, str]:
        """尝试执行补签逻辑"""
        user_ext = await CurrencyService.get_user_extend(session, user_id)
        if not user_ext:
            return False, "⚠️ 用户数据不存在。"

        today = now().date()
        last_date = user_ext.last_checkin_date

        if not last_date:
            return False, "⚠️ 你还没有签到过，无法使用补签卡。"

        gap = (today - last_date).days

        # 情况 1: 今天还没签，且断签 1 天 (例如今天 27, 上次 25。Gap=2)
        if gap == 2:
            # 补签昨天 (Today-1)
            # 逻辑：将 last_checkin_date 设为昨天，streak + 1
            # 这样用户今天再签到时，streak 会继续 +1
            user_ext.last_checkin_date = today - timedelta(days=1)
            user_ext.streak_days += 1

            # 更新最大连签
            user_ext.max_streak_days = max(user_ext.max_streak_days, user_ext.streak_days)

            session.add(user_ext)
            return True, f"✅ 成功补签 {user_ext.last_checkin_date}！\n当前连签已恢复为 {user_ext.streak_days} 天。\n⚠️ 请记得今天也要签到哦！"

        # 情况 2: 今天已经签了 (Gap=0)，但昨天断签导致 streak 重置为 1
        if gap == 0:
            if user_ext.streak_days > 1:
                return False, "📅 你的连签状态正常，无需补签。"

            # 查找上一条签到记录 (排除今天)
            stmt = select(CurrencyTransactionModel).where(
                CurrencyTransactionModel.user_id == user_id,
                CurrencyTransactionModel.event_type == "daily_checkin",
                func.date(CurrencyTransactionModel.created_at) < today
            ).order_by(CurrencyTransactionModel.created_at.desc()).limit(1)

            result = await session.execute(stmt)
            last_tx = result.scalar_one_or_none()

            if not last_tx:
                return False, "🤔 找不到之前的签到记录，无法恢复连签。"

            last_tx_date = last_tx.created_at.date()
            gap_tx = (today - last_tx_date).days

            if gap_tx == 1:
                 return False, "📅 你的连签状态正常，无需补签。"

            # TODO: 这种情况比较复杂，需要修改历史记录才能接上，暂时不支持
            return False, "⚠️ 补签功能暂时只支持在断签的第二天使用。"

        return False, "⚠️ 只能补签昨天的签到。"

    @staticmethod
    async def has_unused_ticket(session: AsyncSession, user_id: int, action_type: str) -> bool:
        """检查是否有未使用的功能券"""
        stmt = select(CurrencyTransactionModel).where(
            CurrencyTransactionModel.user_id == user_id,
            CurrencyTransactionModel.event_type == "purchase",
            CurrencyTransactionModel.is_consumed.is_(False),
            # 使用 JSON 字段中的 action_type 进行过滤
            func.json_extract(CurrencyTransactionModel.meta, "$.action_type") == action_type
        ).limit(1)

        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def consume_ticket(session: AsyncSession, user_id: int, action_type: str) -> bool:
        """消耗一张功能券 (将最早的一张未消耗记录标记为已消耗)"""
        # 查找最早的一张未消耗券
        stmt = select(CurrencyTransactionModel).where(
            CurrencyTransactionModel.user_id == user_id,
            CurrencyTransactionModel.event_type == "purchase",
            CurrencyTransactionModel.is_consumed.is_(False),
            func.json_extract(CurrencyTransactionModel.meta, "$.action_type") == action_type
        ).order_by(CurrencyTransactionModel.created_at.asc()).limit(1)

        result = await session.execute(stmt)
        ticket = result.scalar_one_or_none()

        if ticket:
            ticket.is_consumed = True
            session.add(ticket)
            await session.commit()
            return True

        return False
