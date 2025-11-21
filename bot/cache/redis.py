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
    """简单的内存缓存实现，替代Redis"""

    def __init__(self) -> None:
        self._cache = {}
        self._expiry = {}

    async def get(self, key: str) -> bytes | None:
        """获取缓存值"""
        if key in self._expiry and time.time() > self._expiry[key]:
            # 过期了，删除
            self._cache.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._cache.get(key)

    async def set(self, key: str, value: bytes | str, ex: int | None = None) -> None:
        """设置缓存值"""
        self._cache[key] = value
        if ex:
            self._expiry[key] = time.time() + ex

    async def delete(self, key: str) -> None:
        """删除缓存值"""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)


# 创建内存缓存实例
memory_cache = MemoryCache()


def build_key(*args: Args, **kwargs: Kwargs) -> str:
    """Build a string key based on provided arguments and keyword arguments."""
    args_str = ":".join(map(str, args))
    kwargs_str = ":".join(f"{key}={value}" for key, value in sorted(kwargs.items()))
    return f"{args_str}:{kwargs_str}"


async def set_redis_value(
    key: bytes | str,
    value: bytes | str,
    ttl: int | timedelta | None = DEFAULT_TTL,
    is_transaction: bool = False,
) -> None:
    """Set a value in memory cache with an optional time-to-live (TTL)."""
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
    """Caches the function's return value into a key generated with module_name, function_name, and args.

    Args:
        ttl (int | timedelta): Time-to-live for the cached value.
        namespace (str): Namespace for cache keys.
        cache (Redis): Redis instance for storing cached data.
        key_builder (Callable[..., str]): Function to build cache keys.
        serializer (AbstractSerializer | None): Serializer for cache data.

    Returns:
        Callable: A decorator that wraps the original function with caching logic.

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
                return serializer.deserialize(cached_value)

            # If not in cache, call the original function
            result = await func(*args, **kwargs)

            # Store the result in Redis
            await set_redis_value(
                key=key,
                value=serializer.serialize(result),
                ttl=ttl,
            )

            return result

        return wrapper

    return decorator


async def clear_cache(
    func: Callable[..., Awaitable[Any]],
    *args: Args,
    **kwargs: Kwargs,
) -> None:
    """Clear the cache for a specific function and arguments.

    Parameters
    ----------
    - func (Callable): The target function for which the cache needs to be cleared.
    - args (Args): Positional arguments passed to the function.
    - kwargs (Kwargs): Keyword arguments passed to the function.

    Keyword Arguments:
    - namespace (str, optional): A string indicating the namespace for the cache. Defaults to "main".

    """
    namespace = kwargs.get("namespace", "main")

    key = build_key(*args, **kwargs)
    key = f"{namespace}:{func.__module__}:{func.__name__}:{key}"

    await memory_cache.delete(key)
