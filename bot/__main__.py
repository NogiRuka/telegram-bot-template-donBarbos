from __future__ import annotations
import asyncio
from pathlib import Path

from loguru import logger
from bot.core.config import settings

from bot.core.loader import bot, dp
from bot.handlers import get_handlers_router
from bot.keyboards.default_commands import remove_default_commands, set_default_commands
from bot.middlewares import register_middlewares


async def on_startup() -> None:
    """启动钩子

    功能说明：
    - 注册中间件与路由
    - 设置默认命令
    - 输出机器人基本信息

    输入参数：
    - 无

    返回值：
    - None
    """
    logger.info("机器人启动中...")

    register_middlewares(dp)

    dp.include_router(get_handlers_router())

    await set_default_commands(bot)

    # 统一服务清单由外部启动脚本打印，这里仅输出机器人基本信息

    logger.info("机器人启动完成")


async def on_shutdown() -> None:
    """关闭钩子

    功能说明：
    - 移除默认命令
    - 关闭存储与网络会话

    输入参数：
    - 无

    返回值：
    - None
    """
    logger.info("机器人停止中...")

    await remove_default_commands(bot)

    await dp.storage.close()
    await dp.fsm.storage.close()

    await bot.session.close()

    logger.info("机器人已停止")


# 已移除 Webhook 相关逻辑，专注轮询模式


async def main() -> None:
    """主入口函数

    功能说明：
    - 初始化本地日志
    - 注册启动与关闭钩子
    - 以轮询模式启动机器人

    输入参数：
    - 无

    返回值：
    - None
    """
    # 已移除 Sentry 集成，仅使用本地日志

    Path("logs/bot").mkdir(parents=True, exist_ok=True)
    logger.add(
        "logs/bot/bot.log",
        level="DEBUG",
        format="{time} | {level} | {module}:{function}:{line} | {message}",
        rotation="100 KB",
        compression="zip",
    )
    print_boot_banner("Bot")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.exception(f"轮询启动失败：{e}")
        raise


def mask_database_url(url: str) -> str:
    """数据库URL脱敏

    功能说明：
    - 对包含账户密码的数据库URL进行脱敏，隐藏密码部分

    输入参数：
    - url: 数据库连接URL字符串

    返回值：
    - 脱敏后的URL字符串
    """
    try:
        at = url.find("@")
        scheme_end = url.find("://")
        if at == -1 or scheme_end == -1:
            return url
        cred = url[scheme_end + 3 : at]
        if ":" in cred:
            user = cred.split(":", 1)[0]
            masked = f"{user}:***"
        else:
            masked = cred
        return url[: scheme_end + 3] + masked + url[at:]
    except Exception:
        return url


def get_services_info() -> dict:
    """保留函数占位以兼容旧调用（已不再在此打印服务清单）

    功能说明：
    - 返回空的或最小化的服务信息，统一由外部脚本负责展示

    输入参数：
    - 无

    返回值：
    - dict: 服务信息字典（最小化）
    """
    return {}


if __name__ == "__main__":
    asyncio.run(main())


def print_boot_banner(service_name: str) -> None:
    """打印启动 Banner（每次启动）

    功能说明：
    - 读取 `assets/banner.txt` 的文本内容并打印到日志（控制台与文件）
    - 不使用任何标记文件，每次进程启动都会打印一次

    输入参数：
    - service_name: 服务名称说明（例如 "API"、"Bot"），用于日志定位

    返回值：
    - None
    """
    try:
        banner_path = Path("assets/banner.txt")
        text = ""
        if banner_path.exists():
            try:
                raw = banner_path.read_text(encoding="utf-8", errors="ignore")
                cleaned = sanitize_banner_text(raw)
                compact_line = build_start_info_line("Bot")
                sep = _make_separator(cleaned, compact_line)
                logger.info("\n{}\n{}\n{}", cleaned, sep, compact_line)
            except Exception as e:
                compact_line = build_start_info_line("Bot")
                logger.info("{}\n{}", f"{service_name} 启动", compact_line)
                logger.warning("读取 banner 失败: {}", e)
        else:
            compact_line = build_start_info_line("Bot")
            logger.info("{}\n{}", f"{service_name} 启动", compact_line)
    except Exception:
        # 忽略打印失败，保证启动不中断
        pass


def build_start_info_line(module_name: str) -> str:
    """构建启动信息紧凑行

    功能说明：
    - 构造一行文本，在 banner 下方显示，使用分隔符与 emoji 装饰
    - 仅包含项目名与模块名，例如："🚀 项目: Telegram Bot Admin | 🧩 模块: Bot"

    输入参数：
    - module_name: 模块名称（例如 "API"、"Bot"）

    返回值：
    - str: 单行启动信息
    """
    try:
        project = "Telegram Bot Admin"
        return f"🚀 项目: {project} | 🧩 模块: {module_name}"
    except Exception:
        return f"🚀 项目: Telegram Bot Admin | 🧩 模块: {module_name}"


def sanitize_banner_text(text: str) -> str:
    """清理 banner 文本的空行与尾随空格

    功能说明：
    - 去除每行末尾的空格
    - 去除头尾的空白行
    - 将连续空白行压缩为一行

    输入参数：
    - text: 原始 banner 文本

    返回值：
    - str: 清理后的 banner 文本
    """
    try:
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
    except Exception:
        return text


def _make_separator(banner_text: str, info_line: str) -> str:
    """生成分隔线

    功能说明：
    - 根据 banner 最长行与信息行长度，生成一条由 '─' 组成的分隔线

    输入参数：
    - banner_text: 清理后的 banner 文本
    - info_line: 单行启动信息文本

    返回值：
    - str: 分隔线文本
    """
    try:
        banner_lines = banner_text.splitlines() if banner_text else []
        w_banner = max((len(ln) for ln in banner_lines), default=0)
        w_info = len(info_line)
        width = max(w_banner, w_info, 32)
        return "─" * width
    except Exception:
        return "─" * max(len(info_line), 32)


# 已移除居中对齐逻辑，改为紧凑单行输出
