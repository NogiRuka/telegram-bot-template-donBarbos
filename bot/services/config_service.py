from __future__ import annotations
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.config import ConfigModel, ConfigType


async def get_config(session: AsyncSession, key: str) -> Any:
    """读取配置键

    功能说明:
    - 从 `config` 表读取指定键并返回类型化值

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名

    返回值:
    - Any: 类型化后的配置值，若不存在返回 None
    """
    try:
        result = await session.execute(select(ConfigModel).where(ConfigModel.key == key))
        model: ConfigModel | None = result.scalar_one_or_none()
        return model.get_typed_value() if model else None
    except Exception:
        return None


async def set_config(session: AsyncSession, key: str, value: Any, config_type: ConfigType | None = None) -> bool:
    """写入配置键

    功能说明:
    - 将指定键写入到 `config` 表，若不存在则创建，存在则更新

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名
    - value: 要写入的值
    - config_type: 值类型，缺省时遵循原类型或推断为字符串

    返回值:
    - bool: True 表示写入成功
    """
    try:
        result = await session.execute(select(ConfigModel).where(ConfigModel.key == key))
        model: ConfigModel | None = result.scalar_one_or_none()
        if model is None:
            model = ConfigModel(key=key, value=str(value))
            if config_type:
                model.config_type = config_type
            session.add(model)
        else:
            await session.execute(
                update(ConfigModel).where(ConfigModel.id == model.id).values(value=str(value))
            )
        await session.commit()
        return True
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        return False


async def toggle_config(session: AsyncSession, key: str) -> bool:
    """切换布尔配置键

    功能说明:
    - 将布尔类型的键值翻转并保存

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名

    返回值:
    - bool: 新的布尔值；若操作失败返回 False
    """
    try:
        result = await session.execute(select(ConfigModel).where(ConfigModel.key == key))
        model: ConfigModel | None = result.scalar_one_or_none()
        current = False
        if model:
            typed = model.get_typed_value()
            current = bool(typed) if typed is not None else False
        new_value = not current
        await set_config(session, key, str(new_value), ConfigType.BOOLEAN)
        return new_value
    except Exception:
        return False


async def list_features(session: AsyncSession) -> dict[str, bool]:
    """列出功能开关

    功能说明:
    - 返回常见功能开关的布尔值集合

    输入参数:
    - session: 异步数据库会话

    返回值:
    - dict[str, bool]: 功能键到布尔值的映射
    """
    keys = ["bot_enabled", "features_enabled", "feature_export_users"]
    out: dict[str, bool] = {}
    for k in keys:
        val = await get_config(session, k)
        out[k] = bool(val) if val is not None else False
    return out

