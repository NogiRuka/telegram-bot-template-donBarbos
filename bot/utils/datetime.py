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
    if re.match(r"^[+-]\d{2}:\d{2}$", tzname):
        sign = 1 if tzname.startswith("+") else -1
        hours = int(tzname[1:3])
        minutes = int(tzname[4:6])
        return datetime.timezone(datetime.timedelta(hours=sign * hours, minutes=sign * minutes))
    with contextlib.suppress(Exception):
        return ZoneInfo(tzname)
    # 当系统缺少 IANA 时区数据库时, 回退到偏移字符串
    try:
        tzoffset = settings.get_timezone_offset_str()
        sign = 1 if tzoffset.startswith("+") else -1
        hours = int(tzoffset[1:3])
        minutes = int(tzoffset[4:6])
        return datetime.timezone(datetime.timedelta(hours=sign * hours, minutes=sign * minutes))
    except Exception:  # noqa: BLE001
        return UTC


def parse_datetime(s: Any) -> datetime.datetime | None:
    """解析日期字符串为应用时区 datetime (精度到秒)

    功能说明:
    - 支持多种格式：'2025-12-21 20:13:14'、ISO格式等
    - 去除微秒精度, 只保留到秒
    - 统一转换为应用时区 (去除tzinfo)

    输入参数:
    - s: 任意类型的日期字符串 (如 '2025-12-21 20:13:14')

    返回值:
    - datetime | None: 成功解析返回 datetime (应用时区, 精度到秒), 失败返回 None
    """
    if not s:
        return None
    try:
        text = str(s).strip()

        # 如果是标准格式 2025-12-21 20:13:14, 直接解析
        if len(text) == 19 and text[4] == "-" and text[7] == "-" and text[10] == " " and text[13] == ":" and text[16] == ":":
            dt = datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            return dt.replace(microsecond=0)

        # 如果是ISO格式, 使用原来的解析逻辑
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        dt = datetime.datetime.fromisoformat(text)
        app_tz = get_app_timezone()
        local = dt.replace(tzinfo=app_tz) if dt.tzinfo is None else dt.astimezone(app_tz)
        return local.replace(microsecond=0, tzinfo=None)
    except ValueError as e:
        logger.debug(f"🔍 无法解析日期字段: {s}, 错误: {e}")
        return None


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
        local = dt.replace(tzinfo=app_tz) if dt.tzinfo is None else dt.astimezone(app_tz)
        return local.replace(microsecond=0, tzinfo=None)
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
    base = dt if dt.tzinfo is not None else dt.replace(tzinfo=get_app_timezone())
    local_dt = base.astimezone(tz)
    return local_dt.strftime(fmt)


def parse_formatted_datetime(s: str | None) -> datetime.datetime | None:
    """解析格式化的日期时间字符串 (YYYY-MM-DD HH:MM:SS)

    功能说明:
    - 将格式化的日期时间字符串转为 Python datetime
    - 假设输入时间为应用时区的时间
    - 返回带应用时区信息的 datetime 对象

    输入参数:
    - s: 格式化日期时间字符串 (如 '2025-12-21 14:30:00')

    返回值:
    - datetime | None: 成功解析返回 datetime (应用时区), 失败返回 None
    """
    if not s:
        return None
    try:
        # 解析为 naive datetime (无时区信息)
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


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
    base = dt if dt.tzinfo is not None else dt.replace(tzinfo=get_app_timezone())
    app_tz = get_app_timezone()
    iso = base.astimezone(app_tz).isoformat(timespec="seconds")
    # 若为 UTC 则统一使用 Z
    return iso.replace("+00:00", "Z")


def now() -> datetime.datetime:
    """获取当前应用时区的时间 (无时区信息, 精度到秒)

    功能说明:
    - 返回当前时间, 转换为应用配置时区
    - 去除 tzinfo, 方便写入数据库
    - 去除微秒

    输入参数:
    - 无

    返回值:
    - datetime.datetime: 当前时间 (Naive)
    """
    dt = datetime.datetime.now(datetime.timezone.utc)
    app_tz = get_app_timezone()
    local = dt.astimezone(app_tz)
    return local.replace(microsecond=0, tzinfo=None)


def get_friendly_timezone_name(tz_name: str) -> str:
    # 优先匹配常用映射
    timezone_map = {
        "Asia/Shanghai": "北京时间",
        "Asia/Tokyo": "东京时间",
        "UTC": "协调世界时 (UTC)"
    }

    if tz_name in timezone_map:
        return timezone_map[tz_name]

    # 如果不在映射里，对名称进行美化处理：'Europe/Paris' -> 'Paris (Europe)'
    if "/" in tz_name:
        region, city = tz_name.split("/")
        return f"{city.replace('_', ' ')} ({region})"

    return tz_name


def format_duration(seconds: int | float | None) -> str:
    """格式化时长为人类可读格式 (HH:MM:SS 或 MM:SS)

    功能说明:
    - 将秒数转换为 HH:MM:SS 或 MM:SS 格式
    - 自动处理 None 或 0 值

    输入参数:
    - seconds: 总秒数 (int 或 float)

    返回值:
    - str: 格式化后的时长字符串 (如 "01:30", "01:20:30")
    """
    if not seconds:
        return "00:00"
    
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
