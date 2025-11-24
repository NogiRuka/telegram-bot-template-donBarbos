from __future__ import annotations
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from bot.cache.serialization import AbstractSerializer, PickleSerializer

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import timedelta


DEFAULT_TTL = 10

_Func = TypeVar("_Func")
Args = str | int  # basically only user_id is used as identifier
Kwargs = Any


# 简单的内存缓存实现
class MemoryCache:
    """简单的内存缓存实现，替代 Redis

    功能说明:
    - 使用本地字典存储键值对，支持过期时间 TTL

    输入参数:
    - 无

    返回值:
    - 无
    """

    def __init__(self) -> None:
        self._cache = {}
        self._expiry = {}

    async def get(self, key: str) -> bytes | str | None:
        """获取缓存值

        功能说明:
        - 返回未过期的缓存内容

        输入参数:
        - key: 键

        返回值:
        - bytes | str | None: 缓存内容或 None
        """
        if key in self._expiry and time.time() > self._expiry[key]:
            # 过期了，删除
            self._cache.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._cache.get(key)

    async def set(self, key: str, value: bytes | str, ex: int | None = None) -> None:
        """设置缓存值

        功能说明:
        - 设置键值并可选设置过期时间（秒）

        输入参数:
        - key: 键
        - value: 值（bytes 或 str）
        - ex: 过期时间（秒），None 表示不过期

        返回值:
        - None
        """
        self._cache[key] = value
        if ex:
            self._expiry[key] = time.time() + ex

    async def delete(self, key: str) -> None:
        """删除缓存值

        功能说明:
        - 删除键及其过期记录

        输入参数:
        - key: 键

        返回值:
        - None
        """
        self._cache.pop(key, None)
        self._expiry.pop(key, None)


# 创建内存缓存实例
memory_cache = MemoryCache()


def build_key(*args: Args, **kwargs: Kwargs) -> str:
    """构建缓存键

    功能说明:
    - 基于入参生成稳定的字符串键，保证同参命中同一缓存条目

    输入参数:
    - args: 位置参数（如 user_id）
    - kwargs: 关键字参数

    返回值:
    - str: 生成的键
    """
    args_str = ":".join(map(str, args))
    kwargs_str = ":".join(f"{key}={value}" for key, value in sorted(kwargs.items()))
    return f"{args_str}:{kwargs_str}"


async def set_cache_value(
    key: bytes | str,
    value: bytes | str,
    ttl: int | timedelta | None = DEFAULT_TTL,
    is_transaction: bool = False,
) -> None:
    """设置缓存值

    功能说明:
    - 写入缓存，并支持指定 TTL（秒或 `timedelta`）

    输入参数:
    - key: 键（bytes 或 str）
    - value: 值（bytes 或 str）
    - ttl: 过期时间，整数或 `timedelta`，None 表示不过期
    - is_transaction: 事务标志（占位，未使用）

    返回值:
    - None
    """
    ttl_seconds = None
    if ttl:
        ttl_seconds = int(ttl.total_seconds()) if hasattr(ttl, "total_seconds") else int(ttl)

    await memory_cache.set(str(key), value, ttl_seconds)


def cached(
    ttl: int | timedelta = DEFAULT_TTL,
    namespace: str = "main",
    cache: MemoryCache = memory_cache,
    key_builder: Callable[..., str] = build_key,
    serializer: AbstractSerializer | None = None,
) -> Callable[[Callable[..., Awaitable[_Func]]], Callable[..., Awaitable[_Func]]]:
    """缓存异步函数返回值

    功能说明:
    - 以 `namespace:module:function:key` 为键，把函数返回值序列化后存入缓存
    - 命中缓存时反序列化并返回，未命中则执行函数并写入缓存

    输入参数:
    - ttl: 过期时间（秒或 `timedelta`）
    - namespace: 命名空间前缀，区分不同模块
    - cache: 缓存实现（默认内存缓存，可替换 Redis 客户端）
    - key_builder: 键构建函数
    - serializer: 序列化器，默认 `PickleSerializer`

    返回值:
    - Callable: 装饰器，包装原函数以加入缓存行为

    异步/同步说明:
    - 该装饰器仅用于异步函数（`async def`），返回 `Awaitable`
    """
    if serializer is None:
        serializer = PickleSerializer()

    def decorator(func: Callable[..., Awaitable[_Func]]) -> Callable[..., Awaitable[_Func]]:
        @wraps(func)
        async def wrapper(*args: Args, **kwargs: Kwargs) -> Any:
            key = key_builder(*args, **kwargs)
            key = f"{namespace}:{func.__module__}:{func.__name__}:{key}"

            # Check if the key is in the cache
            cached_value = await cache.get(key)
            if cached_value is not None:
                try:
                    return serializer.deserialize(cached_value)
                except Exception:  # noqa: BLE001
                    await cache.delete(key)

            # If not in cache, call the original function
            result = await func(*args, **kwargs)

            # 序列化失败时不写缓存，仅返回计算结果
            try:
                serialized = serializer.serialize(result)
                await set_cache_value(key=key, value=serialized, ttl=ttl)
            except Exception:  # noqa: BLE001
                pass

            return result

        return wrapper

    return decorator


async def clear_cache(
    func: Callable[..., Awaitable[Any]],
    *args: Args,
    **kwargs: Kwargs,
) -> None:
    """清理指定函数与入参的缓存

    功能说明:
    - 生成与 `cached` 装饰器一致的键并删除对应缓存项

    输入参数:
    - func: 目标函数（与缓存的函数一致）
    - args: 位置参数
    - kwargs: 关键字参数；支持可选 `namespace`

    返回值:
    - None
    """
    namespace = kwargs.get("namespace", "main")
    # 避免将控制参数纳入键生成，确保键一致性
    if "namespace" in kwargs:
        kwargs = {k: v for k, v in kwargs.items() if k != "namespace"}

    key = build_key(*args, **kwargs)
    key = f"{namespace}:{func.__module__}:{func.__name__}:{key}"

    await memory_cache.delete(key)
