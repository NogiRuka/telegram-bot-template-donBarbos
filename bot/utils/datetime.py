"""日期时间处理工具函数

提供统一的日期时间解析、格式化功能。
存储时使用不带时区的 UTC 时间（精度到秒），显示时根据时区转换。
"""

from __future__ import annotations

import datetime
from typing import Any
from zoneinfo import ZoneInfo

from loguru import logger


# 默认时区
DEFAULT_TIMEZONE = ZoneInfo("Asia/Shanghai")


def parse_iso_datetime(s: Any) -> datetime.datetime | None:
    """解析 ISO 日期字符串为 datetime（不带时区，精度到秒）

    功能说明:
    - 将 Emby 等 API 返回的 ISO 日期字符串转为 Python datetime
    - 去除微秒精度，只保留到秒
    - 转换为 UTC 后移除时区信息，存储为 naive datetime

    输入参数:
    - s: 任意类型的日期字符串（如 '2025-12-07T14:30:00.123456Z'）

    返回值:
    - datetime | None: 成功解析返回 datetime（无时区，精度到秒），失败返回 None
    """
    if not s:
        return None
    try:
        text = str(s)
        # 处理 Z 后缀
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(text)
        # 转换为 UTC 并移除时区信息
        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        # 去除微秒，只保留到秒
        dt = dt.replace(microsecond=0)
        return dt
    except ValueError:
        logger.debug(f"🔍 无法解析日期字段: {s}")
        return None


def format_datetime(
    dt: datetime.datetime | None,
    tz: ZoneInfo | None = None,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """格式化 datetime 为指定时区的字符串

    功能说明:
    - 将存储的 naive datetime（UTC）转换为指定时区后格式化

    输入参数:
    - dt: datetime 对象（应为 naive UTC 时间）
    - tz: 目标时区，默认为 Asia/Shanghai
    - fmt: 格式化字符串，默认 '%Y-%m-%d %H:%M:%S'

    返回值:
    - str: 格式化后的日期字符串，dt 为 None 时返回 '-'
    """
    if dt is None:
        return "-"
    if tz is None:
        tz = DEFAULT_TIMEZONE
    # 假设存储的是 UTC 时间
    utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime(fmt)


def to_iso_string(dt: datetime.datetime | None) -> str | None:
    """将 datetime 转为 ISO 格式字符串（带 Z 后缀）

    功能说明:
    - 用于需要输出 ISO 格式的场景

    输入参数:
    - dt: datetime 对象

    返回值:
    - str | None: ISO 格式字符串，dt 为 None 时返回 None
    """
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

