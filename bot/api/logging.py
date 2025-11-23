"""Uvicorn 日志工具

功能说明:
- 提供静默 Uvicorn 的辅助函数, 控制日志等级与访问日志
- 提供 API 文件日志初始化函数, 输出到 `logs/api/` 目录, 按日切分

依赖安装(Windows):
- pip install uvicorn loguru
"""
from __future__ import annotations
import logging
from pathlib import Path

from loguru import logger


def quiet_uvicorn_logs() -> None:
    """静默 Uvicorn 日志

    功能说明:
    - 将 `uvicorn` 与 `uvicorn.error` 设置为 WARNING, 关闭 `uvicorn.access`

    输入参数:
    - 无

    返回值:
    - None
    """
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").disabled = True


def setup_api_logging(debug: bool = False) -> None:
    """初始化 API 文件日志

    功能说明:
    - 创建 `logs/api` 目录并添加 loguru 文件日志输出
    - 主日志与错误日志分离, 均启用异步队列
    - 每天午夜切分新文件(`rotation="00:00"`), 不压缩(`compression=None`), 永久保留(`retention=None`)

    输入参数:
    - debug: 是否使用调试日志等级, 影响主日志级别

    返回值:
    - None
    """
    try:
        Path("logs/api").mkdir(parents=True, exist_ok=True)
        # 主日志: 根据 debug 选择等级, 异步队列, 每日切分, 不压缩, 永久保留
        logger.add(
            "logs/api/api.log",
            level="DEBUG" if debug else "INFO",
            format="{time} | {level} | {module}:{function}:{line} | {message}",
            rotation="00:00",
            retention=None,
            enqueue=True,
            compression=None,
        )
        # 错误日志: 仅记录 ERROR 及以上, 异步队列, 每日切分, 不压缩, 永久保留
        logger.add(
            "logs/api/api.error.log",
            level="ERROR",
            format="{time} | {level} | {module}:{function}:{line} | {message}",
            rotation="00:00",
            retention=None,
            enqueue=True,
            compression=None,
        )
        # 控制台彩色输出在独立运行入口中配置, 避免与 Bot 的控制台 sink 重复
    except (OSError, ValueError) as err:
        logger.warning("初始化 API 文件日志失败: {}", err)
