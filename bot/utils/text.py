from __future__ import annotations


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

