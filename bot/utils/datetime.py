"""日期时间处理工具函数

提供统一的日期时间解析、格式化功能。
时区来源于环境变量 `TIMEZONE`，精度到秒。
"""

from __future__ import annotations
import contextlib
import datetime
import re
from typing import Any
from zoneinfo import ZoneInfo

from loguru import logger

from bot.core.config import settings

# UTC 时区
UTC = datetime.timezone.utc


def get_app_timezone() -> datetime.tzinfo:
    """
    获取应用配置的时区对象

    功能说明:
    - 从配置 `settings.TIMEZONE` 创建并返回 tzinfo
    - 支持 IANA 名称(如 'Asia/Shanghai')与偏移字符串(如 '+08:00')

    输入参数:
    - 无

    返回值:
    - datetime.tzinfo: 时区对象
    """
    tzname = settings.get_timezone_name()
    if tzname.upper() in {"UTC", "Z"}:
        return UTC
    if re.match(r"^[+-]\\d{2}:\\d{2}$", tzname):
        sign = 1 if tzname.startswith("+") else -1
        hours = int(tzname[1:3])
        minutes = int(tzname[4:6])
        return datetime.timezone(datetime.timedelta(hours=sign * hours, minutes=sign * minutes))
    with contextlib.suppress(Exception):
        return ZoneInfo(tzname)
    return UTC


def parse_iso_datetime(s: Any) -> datetime.datetime | None:
    """解析 ISO 日期字符串为应用时区 datetime (精度到秒)

    功能说明:
    - 将 Emby 等 API 返回的 ISO 日期字符串转为 Python datetime
    - 去除微秒精度, 只保留到秒
    - 统一转换为应用时区 (带 tzinfo)

    输入参数:
    - s: 任意类型的日期字符串 (如 '2025-12-07T14:30:00.123456Z')

    返回值:
    - datetime | None: 成功解析返回 datetime (应用时区, 精度到秒), 失败返回 None
    """
    if not s:
        return None
    try:
        text = str(s)

        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        dt = datetime.datetime.fromisoformat(text)
        app_tz = get_app_timezone()
        base = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        local = base.astimezone(app_tz)
        return local.replace(microsecond=0)
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
    - 将 datetime 转换为指定时区后格式化

    输入参数:
    - dt: datetime 对象(建议为 tzinfo=UTC)
    - tz: 目标时区, 默认为应用时区
    - fmt: 格式化字符串, 默认 '%Y-%m-%d %H:%M:%S'

    返回值:
    - str: 格式化后的日期字符串, dt 为 None 时返回 '-'
    """
    if dt is None:
        return "-"
    if tz is None:
        tz = get_app_timezone()
    base = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    local_dt = base.astimezone(tz)
    return local_dt.strftime(fmt)


def to_iso_string(dt: datetime.datetime | None) -> str | None:
    """将 datetime 转为 ISO 格式字符串 (应用时区)

    功能说明:
    - 用于需要输出 ISO 格式的场景 (统一为应用时区, 精度到秒)

    输入参数:
    - dt: datetime 对象

    返回值:
    - str | None: ISO 格式字符串, dt 为 None 时返回 None
    """
    if dt is None:
        return None
    base = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    app_tz = get_app_timezone()
    iso = base.astimezone(app_tz).isoformat(timespec="seconds")
    # 若为 UTC 则统一使用 Z
    return iso.replace("+00:00", "Z")

