from __future__ import annotations
import asyncio
from pathlib import Path

from loguru import logger

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
