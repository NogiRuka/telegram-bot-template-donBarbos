from __future__ import annotations
import asyncio
import contextlib
import shutil
from typing import TYPE_CHECKING, Any

import uvicorn
from aiogram.exceptions import TelegramAPIError, TelegramUnauthorizedError
from aiohttp import ClientError
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from bot.api.app import app as api_app
from bot.api.logging import quiet_uvicorn_logs, setup_api_logging
from bot.core.config import settings
from bot.core.loader import bot, dp
from bot.database.database import engine, sessionmaker
from bot.database.models.base import Base
from bot.handlers import get_handlers_router
from bot.keyboards.default_commands import remove_default_commands, set_default_commands
from bot.services.config_service import ensure_config_defaults
from bot.services.emby_service import save_all_emby_users, cleanup_devices_by_policy

if TYPE_CHECKING:
    from aiogram import Bot


async def on_startup() -> None:
    """启动钩子

    功能说明:
    - 注册中间件与路由并设置默认命令
    - 输出启动状态

    输入参数:
    - 无

    返回值:
    - None
    """
    logger.info("🚀 机器人启动中...")
    dp.include_router(get_handlers_router())
    try:
        await set_default_commands(bot)
    except TelegramUnauthorizedError as err:
        logger.error("⛔ BOT_TOKEN 无效或已撤销: {}", getattr(err, "message", "Unauthorized"))
        raise SystemExit(1) from err
    except (TelegramAPIError, ClientError) as err:
        logger.error("❗ 设置默认命令失败: {}", err)
        raise SystemExit(1) from err
    try:
        await ensure_database_and_schema()
        async with sessionmaker() as session:
            await ensure_config_defaults(session)
            try:
                await save_all_emby_users(session)
                # 启动时执行一次设备清理
                await cleanup_devices_by_policy(session)
            except Exception as err:  # noqa: BLE001
                logger.warning("⚠️ 启动时同步 Emby 用户失败: {}", err)
        await start_api_server()
    except (OSError, ValueError, RuntimeError) as err:
        logger.error("❗ API 服务启动失败: {}", err)
    logger.info("✅ 机器人启动完成")


async def on_shutdown() -> None:
    """关闭钩子

    功能说明:
    - 移除默认命令并关闭存储与会话

    输入参数:
    - 无

    返回值:
    - None
    """
    logger.info("⏹️ 机器人停止中...")
    await remove_default_commands(bot)
    await dp.storage.close()
    await dp.fsm.storage.close()
    await bot.session.close()
    try:
        await engine.dispose()
    except TypeError:
        engine.dispose()
    try:
        await stop_api_server()
    except (RuntimeError, AttributeError) as err:
        logger.warning("⚠️ API 服务停止时发生错误: {}", err)
    logger.info("✅ 机器人已停止")


async def ensure_bot_token_valid(target_bot: Bot) -> None:
    """令牌有效性预检

    功能说明:
    - 调用 Telegram API getMe 验证 BOT_TOKEN 是否有效
    - 失败时记录错误并终止进程

    输入参数:
    - target_bot: Aiogram Bot 实例

    返回值:
    - None
    """
    try:
        await target_bot.get_me()
    except TelegramUnauthorizedError as err:
        logger.error("❌ BOT_TOKEN 无效或已撤销: {}", getattr(err, "message", "Unauthorized"))
        raise SystemExit(1) from err
    except (TelegramAPIError, ClientError) as err:
        logger.error("❌ 无法验证 BOT_TOKEN, 网络或 API 异常: {}", err)
        raise SystemExit(1) from err


async def ensure_database_and_schema() -> None:
    """确保数据库与表结构存在

    功能说明:
    - 若数据库不存在则创建, 使用 UTF8MB4 字符集
    - 使用 SQLAlchemy 元数据在目标数据库中创建所有模型表

    输入参数:
    - 无

    返回值:
    - None
    """
    # 1) 创建不指定数据库的连接, 以便执行 CREATE DATABASE
    password = f":{settings.DB_PASS}" if settings.DB_PASS else ""
    server_url = f"mysql+aiomysql://{settings.DB_USER}{password}@{settings.DB_HOST}:{settings.DB_PORT}/"
    server_engine = create_async_engine(server_url, echo=False, pool_pre_ping=True)

    try:
        async with server_engine.begin() as conn:
            create_db_sql = text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            await conn.execute(create_db_sql)
    finally:
        with contextlib.suppress(Exception):
            await server_engine.dispose()

    # 2) 在目标数据库上创建所有模型表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 已移除运行时 DDL 迁移, 改由外部迁移工具处理


class ApiRuntime:
    """API 运行态容器

    功能说明:
    - 存放 uvicorn Server 与后台任务引用, 避免使用 global 赋值

    输入参数:
    - 无

    返回值:
    - None
    """

    def __init__(self) -> None:
        self.server: Any | None = None
        self.task: asyncio.Task[Any] | None = None
        self.proc: asyncio.subprocess.Process | None = None


api_runtime = ApiRuntime()


async def start_api_server() -> None:
    """启动内嵌 API 服务

    功能说明:
    - 以异步并行方式启动 uvicorn Server, 绑定到 FastAPI 应用
    - 使用配置中的主机与端口

    输入参数:
    - 无

    返回值:
    - None
    """
    quiet_uvicorn_logs()
    setup_api_logging(debug=settings.DEBUG)

    # 优先使用外部进程方式启动 uvicorn, 避免内部 Server 抛出 SystemExit 影响主循环
    uvicorn_bin = shutil.which("uvicorn")
    if uvicorn_bin:
        api_runtime.proc = await asyncio.create_subprocess_exec(
            uvicorn_bin,
            "bot.api.app:app",
            "--host",
            str(settings.API_HOST),
            "--port",
            str(settings.API_PORT),
            "--log-level",
            "critical",
            "--no-access-log",
        )
        logger.info("🌐 API 地址: http://{}:{}", settings.API_HOST, settings.API_PORT)
        return

    # 回退到内嵌方式
    config = uvicorn.Config(
        app=api_app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="critical",
        access_log=False,
        loop="asyncio",
        lifespan="on",
        log_config=None,
    )
    server = uvicorn.Server(config)
    api_runtime.server = server
    api_runtime.task = asyncio.create_task(server.serve())
    logger.info("🌐 API 地址: http://{}:{}", settings.API_HOST, settings.API_PORT)


async def stop_api_server() -> None:
    """停止内嵌 API 服务

    功能说明:
    - 向 uvicorn Server 发送退出信号并等待其结束
    - 在超时情况下放弃等待

    输入参数:
    - 无

    返回值:
    - None
    """
    # 优先停止外部进程
    if api_runtime.proc is not None:
        with contextlib.suppress(ProcessLookupError):
            api_runtime.proc.terminate()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(api_runtime.proc.wait(), timeout=5.0)
        api_runtime.proc = None
        return

    if api_runtime.server is None:
        return
    with contextlib.suppress(AttributeError):
        api_runtime.server.should_exit = True
    if api_runtime.task is not None:
        try:
            await asyncio.wait_for(api_runtime.task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("⚠️ API 服务停止等待超时, 已忽略")
        except SystemExit as err:
            # uvicorn 在部分停止场景会抛出 SystemExit(1), 这里吞掉并记录
            logger.warning("⚠️ API 服务停止返回 SystemExit: {}", err.code if hasattr(err, "code") else err)
        except (RuntimeError, asyncio.CancelledError) as err:
            logger.warning("⚠️ API 服务停止异常: {}", err)
