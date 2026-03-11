from __future__ import annotations
import asyncio
import contextlib
import os
import signal
import sys
from pathlib import Path

from loguru import logger

from bot.core.config import settings
from bot.core.loader import bot, dp
from bot.middlewares import register_middlewares
from bot.runtime.hooks import ensure_bot_token_valid, on_shutdown, on_startup
from bot.utils.banner import print_boot_banner


async def main() -> None:
    """机器人主入口函数。

    执行以下初始化操作：
    1. 初始化本地日志目录
    2. 配置 Loguru 日志系统
    3. 注册全局异常处理钩子
    4. 验证 Bot Token 有效性
    5. 注册中间件和生命周期钩子
    6. 启动长轮询 (Polling)

    Raises:
        asyncio.CancelledError: 当程序接收到停止信号时
        Exception: 启动过程中发生的其他未捕获异常
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
        backtrace=True,
        diagnose=True,
    )

    def _excepthook(exc_type, exc_value, exc_traceback) -> None:
        """全局异常捕获钩子。

        捕获未处理的异常并记录到日志文件中，防止程序意外崩溃时无日志可查。

        Args:
            exc_type: 异常类型
            exc_value: 异常实例
            exc_traceback: 异常堆栈回溯对象
        """
        if issubclass(exc_type, KeyboardInterrupt):
            return
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("❌ 未捕获异常")
    sys.excepthook = _excepthook
    label = os.getenv("BOOT_BANNER_LABEL", "Bot & API")
    print_boot_banner(label)
    await ensure_bot_token_valid(bot)

    register_middlewares(dp)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        loop = asyncio.get_running_loop()
        old_sigint_handler = signal.getsignal(signal.SIGINT)

        polling_task = asyncio.create_task(
            dp.start_polling(
                bot,
                allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"],
            ),
            name="polling",
        )

        shutdown_logged = False

        def _request_shutdown() -> None:
            nonlocal shutdown_logged
            if not shutdown_logged:
                shutdown_logged = True
                logger.info("👋 收到 Ctrl+C, 正在安全停止...")
            if not polling_task.done():
                polling_task.cancel()

        def _handle_sigint(signum: int, frame: object | None) -> None:
            loop.call_soon_threadsafe(_request_shutdown)

        with contextlib.suppress(ValueError, OSError, RuntimeError):
            signal.signal(signal.SIGINT, _handle_sigint)

        try:
            await polling_task
        finally:
            with contextlib.suppress(ValueError, OSError, RuntimeError):
                signal.signal(signal.SIGINT, old_sigint_handler)
    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.exception(f"❗ 轮询启动失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
