from __future__ import annotations
from typing import TYPE_CHECKING, Any

from bot.database.models.config import ConfigType
from bot.services.config_service import get_config, set_config

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# 配置键名
KEY_QUIZ_COOLDOWN_MINUTES = "quiz_cooldown_minutes"
KEY_QUIZ_TRIGGER_PROBABILITY = "quiz_trigger_probability"
KEY_QUIZ_DAILY_LIMIT = "quiz_daily_limit"
KEY_QUIZ_SESSION_TIMEOUT = "quiz_session_timeout"

class QuizConfigService:
    @staticmethod
    async def get_cooldown_minutes(session: AsyncSession) -> int:
        val = await get_config(session, KEY_QUIZ_COOLDOWN_MINUTES)
        return int(val) if val is not None else 10

    @staticmethod
    async def set_cooldown_minutes(session: AsyncSession, value: int, operator_id: int | None = None):
        await set_config(session, KEY_QUIZ_COOLDOWN_MINUTES, value, ConfigType.INTEGER, 10, operator_id)

    @staticmethod
    async def get_trigger_probability(session: AsyncSession) -> float:
        val = await get_config(session, KEY_QUIZ_TRIGGER_PROBABILITY)
        return float(val) if val is not None else 0.05

    @staticmethod
    async def set_trigger_probability(session: AsyncSession, value: float, operator_id: int | None = None):
        await set_config(session, KEY_QUIZ_TRIGGER_PROBABILITY, value, ConfigType.FLOAT, 0.05, operator_id)

    @staticmethod
    async def get_daily_limit(session: AsyncSession) -> int:
        val = await get_config(session, KEY_QUIZ_DAILY_LIMIT)
        return int(val) if val is not None else 10

    @staticmethod
    async def set_daily_limit(session: AsyncSession, value: int, operator_id: int | None = None):
        await set_config(session, KEY_QUIZ_DAILY_LIMIT, value, ConfigType.INTEGER, 10, operator_id)

    @staticmethod
    async def get_session_timeout(session: AsyncSession) -> int:
        val = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
        return int(val) if val is not None else 30

    @staticmethod
    async def set_session_timeout(session: AsyncSession, value: int, operator_id: int | None = None):
        await set_config(session, KEY_QUIZ_SESSION_TIMEOUT, value, ConfigType.INTEGER, 30, operator_id)
