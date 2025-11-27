from __future__ import annotations
import contextlib
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError

from bot.database.models.config import ConfigModel, ConfigType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_config(session: AsyncSession, key: str) -> Any:
    """读取配置键

    功能说明:
    - 从 `config` 表读取指定键并返回类型化值

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名

    返回值:
    - Any: 类型化后的配置值, 若不存在返回 None
    """
    with contextlib.suppress(SQLAlchemyError):
        result = await session.execute(select(ConfigModel).where(ConfigModel.key == key))
        model: ConfigModel | None = result.scalar_one_or_none()
        return model.get_typed_value() if model else None
    return None


async def set_config(session: AsyncSession, key: str, value: Any, config_type: ConfigType | None = None) -> bool:
    """写入配置键

    功能说明:
    - 将指定键写入到 `config` 表, 若不存在则创建, 存在则更新

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名
    - value: 要写入的值
    - config_type: 值类型, 缺省时遵循原类型或推断为字符串

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
                update(ConfigModel).where(ConfigModel.key == key).values(value=str(value))
            )
    except SQLAlchemyError:
        with contextlib.suppress(SQLAlchemyError):
            await session.rollback()
        return False
    else:
        await session.commit()
        return True


async def toggle_config(session: AsyncSession, key: str) -> bool:
    """切换布尔配置键

    功能说明:
    - 将布尔类型的键值翻转并保存

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名

    返回值:
    - bool: 新的布尔值; 若操作失败返回 False
    """
    with contextlib.suppress(SQLAlchemyError):
        result = await session.execute(select(ConfigModel).where(ConfigModel.key == key))
        model: ConfigModel | None = result.scalar_one_or_none()
        current = False
        if model:
            typed = model.get_typed_value()
            current = bool(typed) if typed is not None else False
        new_value = not current
        await set_config(session, key, str(new_value), ConfigType.BOOLEAN)
        return new_value
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
    keys = [
        "bot.enabled",
        "features.enabled",
        "features.export_users",
        "user.register",
        "admin.open_registration",
    ]
    out: dict[str, bool] = {}
    for k in keys:
        val = await get_config(session, k)
        out[k] = bool(val) if val is not None else False
    return out


async def list_admin_permissions(session: AsyncSession) -> dict[str, bool]:
    """列出管理员权限开关

    功能说明:
    - 返回管理员可用功能的授权布尔值集合

    输入参数:
    - session: 异步数据库会话

    返回值:
    - dict[str, bool]: 管理员权限键到布尔值的映射
    """
    keys = [
        "admin.permissions.groups",
        "admin.permissions.stats",
        "admin.permissions.open_registration",
    ]
    out: dict[str, bool] = {}
    for k in keys:
        val = await get_config(session, k)
        out[k] = bool(val) if val is not None else False
    return out


DEFAULT_CONFIGS: dict[str, bool] = {
    # 机器人与全局功能
    "bot.enabled": True,
    "features.enabled": True,
    "features.export_users": False,
    # 用户基础功能
    "user.register": True,
    "user.password": True,
    "user.info": True,
    "user.lines": True,
    "user.devices": True,
    # 管理员功能与权限
    "admin.open_registration": False,
    "admin.permissions.groups": True,
    "admin.permissions.stats": True,
    "admin.permissions.open_registration": True,
}


async def ensure_config_defaults(session: AsyncSession) -> None:
    """初始化配置默认键值

    功能说明:
    - 在启动时确保默认配置键存在, 不存在则以布尔类型写入默认值

    输入参数:
    - session: 异步数据库会话

    返回值:
    - None
    """
    for key, default in DEFAULT_CONFIGS.items():
        current = await get_config(session, key)
        if current is None:
            await set_config(session, key, str(default), ConfigType.BOOLEAN)


async def ensure_config_schema(session: AsyncSession) -> None:
    """校验并迁移配置表结构

    功能说明:
    - 删除不再使用的列, 以适配精简后的模型

    输入参数:
    - session: 异步数据库会话

    返回值:
    - None
    """
    obsolete_cols = [
        "default_value",
        "description",
        "category",
        "display_name",
        "is_public",
        "is_editable",
        "is_system",
        "validation_rule",
        "min_value",
        "max_value",
        "tags",
        "sort_order",
    ]
    for col in obsolete_cols:
        q = text(
            "SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'configs' AND COLUMN_NAME = :col"
        )
        res = await session.execute(q.bindparams(col=col))
        cnt = res.scalar_one() or 0
        if not cnt:
            continue
        try:
            await session.execute(text(f"ALTER TABLE configs DROP COLUMN `{col}`"))
            await session.commit()
        except SQLAlchemyError:
            with contextlib.suppress(SQLAlchemyError):
                await session.rollback()

