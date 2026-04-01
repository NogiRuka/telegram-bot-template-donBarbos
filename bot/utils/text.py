from __future__ import annotations
import html


def safe_alert_text(text: str, max_len: int = 190) -> str:
    """裁剪回调弹窗文本

    功能说明:
    - Telegram CallbackQuery 弹窗文本上限约 200 字符, 本函数将文本裁剪到安全长度

    输入参数:
    - text: 原始文本
    - max_len: 最大长度, 默认 190

    返回值:
    - str: 裁剪后的文本
    """
    s = text or ""
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def safe_message_text(text: str, max_len: int = 4000) -> str:
    """裁剪普通消息文本

    功能说明:
    - Telegram 普通消息文本上限约 4096 字符, 本函数将文本裁剪到安全长度

    输入参数:
    - text: 原始文本
    - max_len: 最大长度, 默认 4000

    返回值:
    - str: 裁剪后的文本
    """
    s = text or ""
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def escape_markdown_v2(text: str) -> str:
    """MarkdownV2 文本转义

    功能说明:
    - 转义 Telegram MarkdownV2 中的特殊字符，避免渲染异常

    输入参数:
    - text: 原始字符串

    返回值:
    - str: 已转义字符串
    """
    specials = r"_()*[]~`>#+-=|{}.!"
    return "".join(f"\\{ch}" if ch in specials else ch for ch in (text or ""))


def build_user_display_name(first_name: str | None, last_name: str | None) -> str:
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    full = f"{first} {last}".strip()
    return full or "Unknown"


def build_user_link_html(user_id: int | str | None, first_name: str | None, last_name: str | None) -> str:
    name = html.escape(build_user_display_name(first_name, last_name))
    uid = str(user_id or "").strip()
    if uid.lstrip("-").isdigit():
        return f'<a href="tg://user?id={uid}">{name}</a>'
    return name


def build_user_link_markdown_v2(user_id: int | str | None, first_name: str | None, last_name: str | None) -> str:
    name = escape_markdown_v2(build_user_display_name(first_name, last_name))
    uid = str(user_id or "").strip()
    if uid.lstrip("-").isdigit():
        return f"[{name}](tg://user?id={uid})"
    return name


def format_size(size_bytes: int | None) -> str:
    """格式化文件大小为人类可读字符串

    功能说明:
    - 使用1024-based转换计算文件大小
    - 自动适配B/KB/MB/GB单位
    - 保留两位小数

    输入参数:
    - size_bytes: 文件大小(字节)

    返回值:
    - str: 格式化后的文件大小字符串
    """
    if size_bytes is None:
        return "未知"

    size = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"
