from __future__ import annotations
import contextlib
import json as _json
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update
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
        if model:
            return model.get_typed_value()
            # 若value为空则取default_value
            return typed_value if typed_value is not None else model.get_typed_default_value()
    return None


async def set_config(
    session: AsyncSession,
    key: str,
    value: Any,
    config_type: ConfigType | None = None,
    default_value: Any | None = None,
    operator_id: int | None = None,
) -> bool:
    """写入配置键

    功能说明:
    - 将指定键写入到 `config` 表, 若不存在则创建, 存在则更新
    - 当提供 `operator_id` 时, 在创建时写入 `created_by`, 在更新时写入 `updated_by`

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名
    - value: 要写入的值
    - config_type: 值类型, 缺省时遵循原类型或推断为字符串
    - default_value: 默认值, 当 `value` 为空时可用作回退
    - operator_id: 操作者用户ID, 用于审计字段 `created_by/updated_by`

    返回值:
    - bool: True 表示写入成功
    """
    try:
        result = await session.execute(select(ConfigModel).where(ConfigModel.key == key))
        model: ConfigModel | None = result.scalar_one_or_none()
        ctype = config_type or (model.config_type if model else ConfigType.STRING)
        if model is None:
            model = ConfigModel(key=key, config_type=ctype)
            model.value = _serialize_value(ctype, value)
            if default_value is not None:
                model.default_value = _serialize_value(ctype, default_value)
            if operator_id is not None:
                with contextlib.suppress(Exception):
                    model.created_by = operator_id
                    model.updated_by = operator_id
            session.add(model)
        else:
            values: dict[str, Any] = {}
            if config_type:
                values["config_type"] = config_type
                ctype = config_type
            values["value"] = _serialize_value(ctype, value)
            if default_value is not None:
                values["default_value"] = _serialize_value(ctype, default_value)
            if operator_id is not None:
                values["updated_by"] = operator_id
            await session.execute(update(ConfigModel).where(ConfigModel.key == key).values(**values))
    except SQLAlchemyError:
        with contextlib.suppress(SQLAlchemyError):
            await session.rollback()
        return False
    else:
        await session.commit()
        return True


async def toggle_config(session: AsyncSession, key: str, operator_id: int | None = None) -> bool:
    """切换布尔配置键

    功能说明:
    - 将布尔类型的键值翻转并保存

    输入参数:
    - session: 异步数据库会话
    - key: 配置键名
    - operator_id: 操作者用户ID, 用于写入审计字段 `updated_by`

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
        await set_config(session, key, new_value, ConfigType.BOOLEAN, operator_id=operator_id)
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
        "bot.features.enabled",
        "user.features.enabled",
        "user.register",
        "user.info",
        "user.lines",
        "user.devices",
        "user.password",
        "user.export_users",
    ]
    out: dict[str, bool] = {}
    for k in keys:
        val = await get_config(session, k)
        out[k] = bool(val) if val is not None else False
    return out


async def get_registration_window(session: AsyncSession) -> dict[str, Any] | None:
    """获取注册时间窗

    功能说明:
    - 从 `config` 表读取管理员设置的注册时间窗 JSON
    - 返回结构: {"start_iso": str, "duration_minutes": int}

    输入参数:
    - session: 异步数据库会话

    返回值:
    - dict | None: 时间窗配置, 若未设置返回 None
    """
    try:
        val = await get_config(session, "admin.open_registration.window")
        if isinstance(val, dict):
            return val
        return None
    except SQLAlchemyError:
        return None


async def get_free_registration_status(session: AsyncSession) -> bool:
    """获取自由注册开关状态

    功能说明:
    - 读取配置 `registration.free_open` 表示是否处于自由注册状态

    输入参数:
    - session: 异步数据库会话

    返回值:
    - bool: True 表示自由注册开启
    """
    try:
        val = await get_config(session, "registration.free_open")
        return bool(val) if val is not None else False
    except SQLAlchemyError:
        return False


async def set_free_registration_status(session: AsyncSession, enabled: bool, operator_id: int | None = None) -> bool:
    """设置自由注册开关状态

    功能说明:
    - 将配置 `registration.free_open` 写入布尔值, 默认值为 False

    输入参数:
    - session: 异步数据库会话
    - enabled: 是否开启自由注册
    - operator_id: 操作者用户ID

    返回值:
    - bool: True 表示写入成功
    """
    return await set_config(
        session,
        "registration.free_open",
        bool(enabled),
        ConfigType.BOOLEAN,
        default_value=False,
        operator_id=operator_id,
    )


async def set_registration_window(
    session: AsyncSession,
    start_iso: str | None,
    duration_minutes: int | None,
    operator_id: int | None = None,
) -> bool:
    """设置注册时间窗

    功能说明:
    - 将注册开始时间与持续分钟写入 JSON 配置 `admin.open_registration.window`

    输入参数:
    - session: 异步数据库会话
    - start_iso: ISO8601 开始时间字符串, 为空表示立即生效
    - duration_minutes: 持续分钟数, 为空表示不限时
    - operator_id: 操作者用户ID

    返回值:
    - bool: True 表示写入成功
    """
    payload: dict[str, Any] = {}
    if start_iso:
        payload["start_iso"] = start_iso
    if duration_minutes is not None:
        payload["duration_minutes"] = int(duration_minutes)
    return await set_config(
        session, "admin.open_registration.window", payload or None, ConfigType.JSON, operator_id=operator_id
    )


async def is_registration_open(session: AsyncSession, now_ts: float | None = None) -> bool:
    """判断注册是否开启且在时间窗内

    功能说明:
    - 综合 `registration.free_open` 自由开关与 `admin.open_registration.window` 时间窗
    - 逻辑: 若自由开关为 True 则直接开放; 否则基于时间窗判断当前是否在可注册区间

    输入参数:
    - session: 异步数据库会话
    - now_ts: 当前时间戳(秒), 缺省使用系统当前UTC时间

    返回值:
    - bool: True 表示注册开放
    """
    try:
        # 自由注册开关优先
        free_open = await get_free_registration_status(session)
        if free_open:
            return True

        # 无自由开关则按时间窗判断
        window = await get_registration_window(session)
        if not window:
            return False

        from datetime import datetime, timedelta, timezone

        # 统一使用 UTC（带 tzinfo，精度到秒）
        _now = (
            datetime.fromtimestamp(now_ts, tz=timezone.utc)
            if now_ts is not None
            else datetime.now(timezone.utc)
        ).replace(microsecond=0)

        start_iso = window.get("start_iso")
        duration = window.get("duration_minutes")
        if not start_iso and duration is None:
            return False

        def _parse_iso_to_utc(text: str) -> datetime | None:
            try:
                s = (text or "").strip()
                if not s:
                    return None
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
                dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                return dt.replace(microsecond=0)
            except ValueError:
                return None

        start = _parse_iso_to_utc(start_iso) if start_iso else _now
        if start is None:
            return False

        if duration is None:
            return _now >= start

        end = start + timedelta(minutes=int(duration))
        return start <= _now <= end
    except SQLAlchemyError:
        return False


async def list_admin_permissions(session: AsyncSession) -> dict[str, bool]:
    """列出管理员权限开关

    功能说明:
    - 返回管理员权限开关的布尔值集合

    输入参数:
    - session: 异步数据库会话

    返回值:
    - dict[str, bool]: 权限键到布尔值的映射
    """
    keys = [
        "admin.features.enabled",
        "admin.groups",
        "admin.stats",
        "admin.hitokoto",
        "admin.open_registration",
        "admin.new_item_notification",
    ]
    out: dict[str, bool] = {}
    for k in keys:
        val = await get_config(session, k)
        out[k] = bool(val) if val is not None else False
    return out


DEFAULT_CONFIGS: dict[str, bool] = {
    "bot.features.enabled": True,
    "user.features.enabled": True,
    "user.register": True,
    "user.password": True,
    "user.info": True,
    "user.lines": True,
    "user.devices": True,
    "admin.features.enabled": True,
    "admin.groups": True,
    "admin.stats": True,
    "admin.open_registration": True,
    "registration.free_open": False,
    "admin.hitokoto": True,
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
            await set_config(session, key, None, ConfigType.BOOLEAN, default_value=default)

    # 初始化 Hitokoto 分类默认值
    current_categories = await get_config(session, "admin.hitokoto.categories")
    if current_categories is None:
        await set_config(session, "admin.hitokoto.categories", None, ConfigType.LIST, default_value=["d", "i"])


# 已移除 ensure_config_schema: 迁移逻辑改由外部管理, 保持代码简洁


def _serialize_value(ctype: ConfigType, value: Any) -> str | None:
    """序列化配置值

    功能说明:
    - 根据配置类型将 Python 值序列化为字符串

    输入参数:
    - ctype: 配置类型
    - value: 原始值

    返回值:
    - str | None: 序列化后的字符串; 若入参为 None 则返回 None
    """
    if value is None:
        return None
    if ctype in (ConfigType.JSON, ConfigType.LIST, ConfigType.DICT):
        return _json.dumps(value, ensure_ascii=False)
    if ctype == ConfigType.BOOLEAN:
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"true", "1", "yes", "on", "y", "t"}:
                return "true"
            if v in {"false", "0", "no", "off", "n", "f", ""}:
                return "false"
            return "true" if len(v) > 0 else "false"
        return "true" if bool(value) else "false"
    if ctype == ConfigType.FLOAT:
        return str(float(value))
    if ctype == ConfigType.INTEGER:
        return str(int(value))
    return str(value)
