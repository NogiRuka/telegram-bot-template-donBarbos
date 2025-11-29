"""
API 包运行入口

功能说明:
- 支持使用命令 `python -m bot.api` 直接启动 FastAPI 服务
- 复用 `bot.api.app` 中的应用实例与工具函数

依赖安装(Windows):
- pip install fastapi uvicorn loguru

命名风格: 统一 snake_case
"""

from __future__ import annotations
import sys

import uvicorn
from loguru import logger

from bot.api.app import app
from bot.api.logging import quiet_uvicorn_logs, setup_api_logging
from bot.core.config import settings
from bot.utils.banner import print_boot_banner


def main() -> None:
    """启动 API 服务

    功能说明:
    - 打印启动横幅与基本信息
    - 压低 uvicorn 日志噪音
    - 按配置的 `API_HOST` 与 `API_PORT` 启动服务

    输入参数:
    - 无

    返回值:
    - None
    """
    logger.remove()
    setup_api_logging(debug=settings.DEBUG)
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
    print_boot_banner("API")
    logger.info(f"🚀 启动 API 服务在 http://{settings.API_HOST}:{settings.API_PORT}")
    quiet_uvicorn_logs()
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="warning" if not settings.DEBUG else "debug",
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
