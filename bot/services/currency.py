"""
经济系统服务模块

提供代币查询、签到、交易记录等核心逻辑。
"""

import random
from datetime import date, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    CurrencyConfigModel,
    CurrencyProductModel,
    CurrencyTransactionModel,
    UserExtendModel,
)
from bot.core.constants import CURRENCY_NAME, CURRENCY_SYMBOL
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
                return False, f"{CURRENCY_SYMBOL} 今日签到已完成，明天再来领取奖励吧！"

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

            if streak > user_ext.max_streak_days:
                user_ext.max_streak_days = streak

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
                f"🎉 签到成功！",
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
    async def add_currency(
        session: AsyncSession,
        user_id: int,
        amount: int,
        event_type: str,
        description: str,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """增加/扣除代币

        输入参数:
        - user_id: 用户ID
        - amount: 变动数值 (正数增加，负数扣除)
        - event_type: 事件类型
        - description: 描述
        - meta: 扩展信息

        返回值:
        - int: 变动后的余额
        """
        user_ext = await CurrencyService.get_user_extend(session, user_id)
        if not user_ext:
            logger.warning(f"⚠️ 尝试给不存在的用户 {user_id} 变更代币")
            return 0

        # 检查余额是否足够 (如果是扣除)
        if amount < 0 and user_ext.currency_balance + amount < 0:
            raise ValueError("💸 余额不足")

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
        )
        session.add(tx)
        await session.commit()
        return user_ext.currency_balance

    @staticmethod
    async def get_products(session: AsyncSession) -> list[CurrencyProductModel]:
        """获取上架商品列表"""
        stmt = select(CurrencyProductModel).where(CurrencyProductModel.is_active.is_(True)).order_by(CurrencyProductModel.price)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_product(session: AsyncSession, product_id: int) -> CurrencyProductModel | None:
        """获取单个商品"""
        stmt = select(CurrencyProductModel).where(CurrencyProductModel.id == product_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

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
            
        # 2. 扣除代币
        try:
            await CurrencyService.add_currency(
                session, 
                user_id, 
                -product.price, 
                "purchase", 
                f"购买 {product.name}", 
                meta={"product_id": product.id, "product_name": product.name}
            )
        except ValueError:
            return False, f"💸 余额不足，需要 {product.price} {CURRENCY_SYMBOL}"
            
        # 3. 扣减库存 (如果是有限库存)
        if product.stock != -1:
            product.stock -= 1
            session.add(product)
            
        # 4. 执行商品效果
        effect_msg = await CurrencyService._handle_product_effect(session, user_id, product)
        
        await session.commit()
            
        return True, f"🛍️ 购买成功！消耗 {product.price} {CURRENCY_SYMBOL}\n{effect_msg}"

    @staticmethod
    async def _handle_product_effect(session: AsyncSession, user_id: int, product: CurrencyProductModel) -> str:
        """处理商品生效逻辑"""
        try:
            if product.action_type == "retro_checkin":
                # 尝试补签逻辑
                # 这里是一个简单的实现示例：检查是否断签，如果断签则恢复一天连签（需完善逻辑）
                # 由于缺乏断签前的数据，这里暂时仅做提示，或者可以实现为增加一次签到机会
                return "✅ 补签卡已使用。请联系管理员确认补签详情（功能完善中）。"
                
            elif product.action_type == "emby_image":
                return "ℹ️ 请联系频道管理员并提供您的图片以修改 Emby 头像。"
                
            elif product.action_type == "custom_title":
                return "ℹ️ 请联系频道管理员设置您的自定义群组头衔。"
                
            return "✅ 商品已发放。"
        except Exception as e:
            logger.exception(f"商品 {product.id} 效果执行失败: {e}")
            return "⚠️ 商品效果执行出现异常，请联系管理员。"

    @staticmethod
    async def ensure_products(session: AsyncSession) -> None:
        """初始化商品数据"""
        products = [
            {
                "id": 1,
                "name": "补签卡",
                "price": 50,
                "category": "tools",
                "action_type": "retro_checkin",
                "description": "用于补签过去未签到的日期（自动使用最近一天）。",
                "stock": -1,
                "is_active": True,
            },
            {
                "id": 2,
                "name": "图像修改",
                "price": 100,
                "category": "emby",
                "action_type": "emby_image",
                "description": "修改 Emby 上的用户图像（购买后请联系频道）。",
                "stock": -1,
                "is_active": True,
            },
            {
                "id": 3,
                "name": "自定义头衔",
                "price": 100,
                "category": "group",
                "action_type": "custom_title",
                "description": "在群组中显示自定义头衔（购买后请联系频道）。",
                "stock": 20,
                "is_active": True,
            },
        ]
        
        for p_data in products:
            stmt = select(CurrencyProductModel).where(CurrencyProductModel.id == p_data["id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                product = CurrencyProductModel(**p_data)
                session.add(product)
            else:
                # 更新关键信息
                existing.name = p_data["name"]
                existing.price = p_data["price"]
                existing.category = p_data["category"]
                existing.action_type = p_data["action_type"]
                existing.description = p_data["description"]
                existing.is_active = p_data["is_active"]
                session.add(existing)
                
        await session.commit()
