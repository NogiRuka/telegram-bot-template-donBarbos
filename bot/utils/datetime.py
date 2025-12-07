"""日期时间处理工具函数

提供统一的日期时间解析、格式化功能。
统一使用 UTC 时区，精度到秒。
"""

from __future__ import annotations
import datetime
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

# UTC 时区
UTC = datetime.timezone.utc


def parse_iso_datetime(s: Any) -> datetime.datetime | None:
    """解析 ISO 日期字符串为 UTC datetime（精度到秒）

    功能说明:
    - 将 Emby 等 API 返回的 ISO 日期字符串转为 Python datetime
    - 去除微秒精度，只保留到秒
    - 统一转换为 UTC（带 tzinfo=UTC）

    输入参数:
    - s: 任意类型的日期字符串 (如 '2025-12-07T14:30:00.123456Z')

    返回值:
    - datetime | None: 成功解析返回 datetime（UTC，精度到秒），失败返回 None
    """
    if not s:
        return None
    try:
        text = str(s)
        original_text = text  # 保存原始值用于日志

        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        dt = datetime.datetime.fromisoformat(text)

        # 记录解析前的值
        logger.debug(f"📅 解析: {original_text} → {dt} (tzinfo={dt.tzinfo})")

        dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)

        dt = dt.replace(microsecond=0)

        logger.debug(f"✅ 最终(UTC): {dt}")
        return dt
    except ValueError as e:
        logger.debug(f"🔍 无法解析日期字段: {s}, 错误: {e}")
        return None


def format_datetime(
    dt: datetime.datetime | None,
    tz: ZoneInfo | None = None,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """格式化 datetime 为指定时区的字符串

    功能说明:
    - 将存储的 UTC datetime 转换为指定时区后格式化

    输入参数:
    - dt: datetime 对象（建议为 tzinfo=UTC）
    - tz: 目标时区，默认为 UTC
    - fmt: 格式化字符串，默认 '%Y-%m-%d %H:%M:%S'

    返回值:
    - str: 格式化后的日期字符串，dt 为 None 时返回 '-'
    """
    if dt is None:
        return "-"
    if tz is None:
        tz = UTC
    base = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    local_dt = base.astimezone(tz)
    return local_dt.strftime(fmt)


def to_iso_string(dt: datetime.datetime | None) -> str | None:
    """将 datetime 转为 ISO 格式字符串（UTC，以 Z 结尾）

    功能说明:
    - 用于需要输出 ISO 格式的场景（统一为 UTC，精度到秒）

    输入参数:
    - dt: datetime 对象

    返回值:
    - str | None: ISO 格式字符串，dt 为 None 时返回 None
    """
    if dt is None:
        return None
    base = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    iso = base.astimezone(UTC).isoformat(timespec="seconds")
    return iso.replace("+00:00", "Z")



