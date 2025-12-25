"""
经济系统服务模块

提供代币查询、签到、交易记录等核心逻辑。
"""

import random
from datetime import date, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    CurrencyConfigModel,
    CurrencyProductModel,
    CurrencyTransactionModel,
    UserExtendModel,
)
from bot.keyboards.inline.constants import CURRENCY_SYMBOL
from bot.utils.datetime import get_app_timezone

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
        # 1. 获取用户数据
        user_ext = await CurrencyService.get_user_extend(session, user_id)
        if not user_ext:
            # 如果不存在，尝试初始化（通常在用户首次交互时已创建）
            # 这里简单返回失败，提示用户先与机器人交互
            return False, "⚠️ 用户数据不存在，请先发送 /start 与机器人交互。"

        # 2. 检查是否已签到
        today = datetime.now(get_app_timezone()).date()
        if user_ext.last_checkin_date == today:
            return False, "📅 今天已经签到过了，明天再来吧！"

        # 3. 读取配置
        base_reward = await CurrencyService.get_config(session, "checkin.base", 20)
        streak_bonus_rate = await CurrencyService.get_config(session, "checkin.streak_bonus_rate", 10)  # 10%
        random_bonus_max = await CurrencyService.get_config(session, "checkin.random_bonus", 5)

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

        total_reward = base_reward + streak_bonus + random_val

        # 6. 更新数据库
        user_ext.last_checkin_date = today
        user_ext.streak_days = streak
        user_ext.currency_balance += total_reward
        user_ext.currency_total += total_reward

        if streak > user_ext.max_streak_days:
            user_ext.max_streak_days = streak

        # 7. 记录流水
        tx = CurrencyTransactionModel(
            user_id=user_id,
            amount=total_reward,
            balance_after=user_ext.currency_balance,
            event_type="daily_checkin",
            description=f"每日签到 (连签 {streak} 天)",
            meta={
                "base": base_reward,
                "streak_bonus": streak_bonus,
                "random": random_val,
                "streak_days": streak,
            },
        )
        session.add(tx)
        await session.commit()

        # TODO: 运势功能后续添加
        msg = (
            f"🎉 签到成功！\n"
            f"获得: +{total_reward} {CURRENCY_SYMBOL}\n"
            f"连续: {streak} 天 (加成 +{int(streak_bonus_pct*100)}%)\n"
            f"当前余额: {user_ext.currency_balance} {CURRENCY_SYMBOL}"
        )
        return True, msg

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
            await session.commit()
            
        return True, f"🛍️ 购买成功！消耗 {product.price} {CURRENCY_SYMBOL}"

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
                "description": "修改 Emby 上的用户图像（购买后请联系管理员）。",
                "stock": -1,
                "is_active": True,
            },
            {
                "id": 3,
                "name": "自定义头衔",
                "price": 200,
                "category": "group",
                "action_type": "custom_title",
                "description": "在群组中显示自定义头衔（购买后请联系管理员）。",
                "stock": -1,
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
