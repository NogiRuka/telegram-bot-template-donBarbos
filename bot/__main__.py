from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path

from loguru import logger

from bot.core.config import settings
from bot.core.loader import bot, dp
from bot.middlewares import register_middlewares
from bot.runtime.hooks import ensure_bot_token_valid, on_shutdown, on_startup
from bot.utils.banner import print_boot_banner


async def main() -> None:
    """主入口函数

    功能说明:
    - 初始化本地日志
    - 注册启动与关闭钩子
    - 以轮询模式启动机器人

    输入参数:
    - 无

    返回值:
    - None
    """
    Path("logs/bot").mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        enqueue=True,
    )
    logger.add(
        "logs/bot/bot.log",
        level="DEBUG" if settings.DEBUG else "INFO",
        format="{time} | {level} | {module}:{function}:{line} | {message}",
        retention=None,
        enqueue=True,
        compression=None,
    )
    logger.add(
        "logs/bot/bot.error.log",
        level="ERROR",
        format="{time} | {level} | {module}:{function}:{line} | {message}",
        retention=None,
        enqueue=True,
        compression=None,
    )
    label = os.getenv("BOOT_BANNER_LABEL", "Bot & API")
    print_boot_banner(label)
    await ensure_bot_token_valid(bot)

    register_middlewares(dp)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.exception(f"❗ 轮询启动失败: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 收到 Ctrl+C, 已安全退出")
