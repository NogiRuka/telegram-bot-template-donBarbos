from __future__ import annotations
from pathlib import Path

from loguru import logger

try:
    from wcwidth import wcwidth as _wc
except ImportError:
    _wc = None
import importlib
import unicodedata


def print_boot_banner(service_name: str) -> None:
    """打印启动 Banner(每次启动)

    功能说明:
    - 读取 `assets/banner.txt` 文本内容并打印到日志(控制台与文件)
    - 不使用任何标记文件, 每次进程启动都会打印一次

    输入参数:
    - service_name: 服务名称说明(例如 "API", "Bot"), 用于日志定位

    返回值:
    - None
    """
    banner_path = Path("assets/banner.txt")
    banner_text = ""
    if banner_path.exists():
        try:
            raw = banner_path.read_text(encoding="utf-8", errors="ignore")
            banner_text = sanitize_banner_text(raw)
        except (OSError, UnicodeDecodeError) as err:
            logger.warning("⚠️ 读取 banner 失败: {}", err)
    value_line = build_start_value_line(service_name)
    box = _make_center_box(banner_text, value_line)
    if banner_text:
        logger.info("\n{}\n{}", banner_text, box)
    else:
        logger.info("{}", box)


def get_project_name() -> str:
    """获取项目名称

    功能说明:
    - 统一从 `bot.core.config.settings.PROJECT_NAME` 读取项目名
    - 若配置模块不可用或字段缺失, 回退为默认值

    输入参数:
    - 无

    返回值:
    - str: 项目名称
    """
    try:
        mod = importlib.import_module("bot.core.config")
        settings = getattr(mod, "settings", None)
        name = getattr(settings, "PROJECT_NAME", None)
        if isinstance(name, str) and name.strip():
            return name.strip()
    except (ModuleNotFoundError, AttributeError, ValueError) as err:
        logger.opt(exception=err).debug("🔍 读取项目名失败, 使用默认值")
    return "telegram-bot-template"


def build_start_value_line(module_name: str) -> str:
    """构建启动信息值行(无属性名)

    功能说明:
    - 仅返回值部分, 不含属性名, 示例: "🚀 Telegram Bot Admin | 🧩 API"
    - 用于在 banner 下方的内容居中显示

    输入参数:
    - module_name: 模块名称(例如 "API", "Bot")

    返回值:
    - str: 单行值文本
    """
    project = get_project_name()
    return f"🚀 {project} | 🧩 {module_name}"


def sanitize_banner_text(text: str) -> str:
    """清理 banner 文本的空行与尾随空格

    功能说明:
    - 去除每行末尾的空格
    - 去除头尾的空白行
    - 将连续空白行压缩为一行

    输入参数:
    - text: 原始 banner 文本

    返回值:
    - str: 清理后的 banner 文本
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    cleaned: list[str] = []
    last_blank = False
    for ln in lines:
        blank = not ln.strip()
        if blank and last_blank:
            continue
        cleaned.append(ln)
        last_blank = blank
    return "\n".join(cleaned)


def _make_center_box(banner_text: str, content_line: str) -> str:
    """生成居中内容的分隔线样式

    功能说明:
    - 根据 banner 最长行宽度与内容长度生成居中内容行
    - 仅保留顶部与底部的水平分隔线, 去掉左右竖线

    输入参数:
    - banner_text: 清理后的 banner 文本
    - content_line: 中间显示的单行文本

    返回值:
    - str: 五行文本(顶线/空白/内容/空白/底线)
    """
    banner_lines = banner_text.splitlines() if banner_text else []
    w_banner = max((len(ln) for ln in banner_lines), default=0)
    content_w = _display_width(content_line)
    inner = max(w_banner, content_w, 32)
    top = "" + "─" * inner + ""
    pad_left = max(0, (inner - content_w) // 2)
    pad_right = max(0, inner - content_w - pad_left)
    empty = " " * inner
    middle = (" " * pad_left) + content_line + (" " * pad_right)
    bottom = "" + "─" * inner + ""
    return f"{top}\n{empty}\n{middle}\n{empty}\n{bottom}"


def _display_width(text: str) -> int:
    """计算字符串在终端中的显示宽度

    功能说明:
    - 优先使用 `wcwidth` 精确计算宽度(支持 emoji 等宽字符)
    - 若不可用, 回退到 `unicodedata.east_asian_width` 的近似计算

    依赖:
    - 可选安装: `pip install wcwidth`

    输入参数:
    - text: 需要计算显示宽度的字符串

    返回值:
    - int: 终端显示宽度(列数)
    """
    width = 0
    if _wc:
        for ch in text:
            w = _wc(ch) or 0
            width += max(w, 0)
        return width
    for ch in text:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("F", "W") else 1
    return width
