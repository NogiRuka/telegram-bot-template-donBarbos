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
        info_lines = build_start_info_lines("Bot")
        text = ""
        if banner_path.exists():
            try:
                text = banner_path.read_text(encoding="utf-8", errors="ignore")
                width = _calc_banner_width(text, info_lines)
                formatted_info = _center_lines(width, info_lines)
                logger.info("\n{}\n{}", text, formatted_info)
            except Exception as e:
                formatted_info = "\n".join(info_lines)
                logger.info("{}\n{}", f"{service_name} 启动", formatted_info)
                logger.warning("读取 banner 失败: {}", e)
        else:
            formatted_info = "\n".join(info_lines)
            logger.info("{}\n{}", f"{service_name} 启动", formatted_info)
    except Exception:
        # 忽略打印失败，保证启动不中断
        pass


def build_start_info_lines(module_name: str) -> list[str]:
    """构建启动项目信息行（精简版）

    功能说明：
    - 仅返回两行信息：项目名与模块名，用于在 banner 下方显示

    输入参数：
    - module_name: 模块名称（例如 "API"、"Bot"）

    返回值：
    - list[str]: 信息行列表
    """
    try:
        project = "Telegram Bot Admin"
        return [f"项目: {project}", f"模块: {module_name}"]
    except Exception:
        return ["项目: Telegram Bot Admin", f"模块: {module_name}"]


def _calc_banner_width(text: str, info_lines: list[str]) -> int:
    """计算用于对齐的宽度

    功能说明：
    - 根据 banner 文本的最长行长度与信息行长度，确定对齐宽度

    输入参数：
    - text: banner 原始文本
    - info_lines: 需对齐的信息行

    返回值：
    - int: 对齐宽度（字符数）
    """
    try:
        banner_lines = [ln.rstrip() for ln in text.splitlines()] if text else []
        banner_width = max((len(ln) for ln in banner_lines), default=0)
        info_width = max((len(ln) for ln in info_lines), default=0)
        return max(banner_width, info_width)
    except Exception:
        return max((len(ln) for ln in info_lines), default=0)


def _center_lines(width: int, lines: list[str]) -> str:
    """将信息行按指定宽度居中对齐

    功能说明：
    - 为每一行计算左侧缩进，使其在给定宽度下居中

    输入参数：
    - width: 对齐宽度
    - lines: 待对齐的文本行

    返回值：
    - str: 对齐后的多行文本
    """
    try:
        centered = []
        for ln in lines:
            ln = ln.rstrip()
            pad = max(0, (width - len(ln)) // 2)
            centered.append(" " * pad + ln)
        return "\n".join(centered)
    except Exception:
        return "\n".join(lines)
