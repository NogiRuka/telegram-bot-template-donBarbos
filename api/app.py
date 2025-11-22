"""
API服务主应用
独立的 FastAPI 应用, 为 React 前端提供数据接口
位于 bot 目录下, 可直接调用 bot 的数据库操作
"""
from __future__ import annotations
import time
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import logging

from api.routes import admins, dashboard, users, webhooks

from bot.core.config import settings

def print_boot_banner_once(service_name: str) -> None:
    """打印启动 Logo（仅首次）

    功能说明：
    - 在 `logs/.boot_banner_printed` 标记文件不存在时，打印一次启动 Logo
    - 使用 loguru 输出到控制台与文件日志

    输入参数：
    - service_name: 服务名称，用于附加说明（如 "API"、"Bot"）

    返回值：
    - None
    """
    try:
        flag = Path("logs/.boot_banner_printed")
        if flag.exists():
            return
        banner = (
            "\n"
            "            ███████╗ █████╗ ██╗  ██╗██╗   ██╗██████╗  █████╗ \n"
            "            ██╔════╝██╔══██╗██║ ██╔╝██║   ██║██╔══██╗██╔══██╗\n"
            "            █████╗  ███████║█████╔╝ ██║   ██║██████╔╝███████║\n"
            "            ██╔══╝  ██╔══██║██╔═██╗ ██║   ██║██╔══██╗██╔══██║\n"
            "            ███████╗██║  ██║██║  ██╗╚██████╔╝██║  ██║██║  ██║\n"
            "            ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝\n"
            "\n"
            "                ✿  ✿  ✿  Sakura Admin / {svc}  ✿  ✿  ✿\n"
        ).format(svc=service_name)
        logger.info(banner)
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("printed", encoding="utf-8")
    except Exception:
        # 忽略打印失败，保证启动不中断
        pass

def setup_api_logging() -> None:
    """初始化 API 文件日志

    功能说明:
    - 创建 `logs/api` 目录并添加 loguru 文件日志输出
    - 根据 `API_DEBUG` 设置日志等级

    输入参数:
    - 无

    返回值:
    - None
    """
    try:
        Path("logs/api").mkdir(parents=True, exist_ok=True)
        logger.add(
            "logs/api/api.log",
            level="DEBUG" if settings.API_DEBUG else "INFO",
            format="{time} | {level} | {module}:{function}:{line} | {message}",
            rotation="100 KB",
            compression="zip",
        )
    except Exception:
        # 避免日志初始化失败影响服务启动
        pass

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    应用生命周期管理

    功能说明:
    - 应用启动与关闭时打印日志

    输入参数:
    - app: FastAPI 应用实例

    返回值:
    - None
    """
    del app
    logger.info("API 服务启动中...")
    yield None
    logger.info("API 服务关闭中...")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 配置好的FastAPI应用实例
    """
    setup_api_logging()
    print_boot_banner_once("API")
    app = FastAPI(
        title="Telegram Bot Admin API",
        description="为Telegram Bot管理界面提供的API服务",
        version="1.0.0",
        lifespan=lifespan
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_api_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(users.router, prefix="/api", tags=["users"])
    app.include_router(admins.router, prefix="/api", tags=["admins"])
    app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
    app.add_api_route("/", webhooks.handle_emby_webhook, methods=["POST"], tags=["webhooks"])

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        请求日志中间件

        功能说明:
        - 在开发阶段输出每个 API 请求的基本信息, 包括方法、路径、状态码与耗时

        输入参数:
        - request: 请求对象
        - call_next: 下游处理器

        返回值:
        - Response: 响应对象
        """
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as err:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception(
                "API {method} {path} error after {ms}ms: {err}",
                method=request.method,
                path=request.url.path,
                ms=duration_ms,
                err=err,
            )
            raise
        else:
            duration_ms = int((time.monotonic() - start) * 1000)
            client = request.client.host if request.client else "-"
            logger.info(
                "API {method} {path} -> {status} {ms}ms from {client}",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=duration_ms,
                client=client,
            )
            return response

    @app.get("/")
    async def root() -> dict[str, str]:
        """
        根路径健康检查

        功能说明:
        - 返回服务运行状态

        输入参数:
        - 无

        返回值:
        - dict[str, str]: 服务状态信息
        """
        return {"message": "Telegram Bot Admin API", "status": "running"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """
        健康检查端点

        功能说明:
        - 返回健康检查状态

        输入参数:
        - 无

        返回值:
        - dict[str, str]: 健康状态信息
        """
        return {"status": "healthy"}

    return app


def quiet_uvicorn_logs() -> None:
    """压低 Uvicorn 日志等级

    功能说明:
    - 将 'uvicorn' 与 'uvicorn.error' 日志等级设为 WARNING
    - 禁用 'uvicorn.access' 访问日志, 避免重复输出

    输入参数:
    - 无

    返回值:
    - None
    """
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").disabled = True


def get_uvicorn_log_config() -> dict[str, object]:
    """生成 Uvicorn 日志配置(压低噪音)

    功能说明:
    - 设置 'uvicorn' 与 'uvicorn.error' 为 WARNING 等级并输出到控制台
    - 移除 'uvicorn.access' 的处理器, 禁止访问日志传播

    输入参数:
    - 无

    返回值:
    - dict[str, object]: logging 配置字典
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(levelname)s: %(message)s"}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            }
        },
        "root": {"level": "WARNING", "handlers": ["console"]},
        "loggers": {
            "uvicorn": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": False},
        },
    }


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    logger.info(f"启动API服务在 http://{settings.API_HOST}:{settings.API_PORT}")
    quiet_uvicorn_logs()
    uvicorn.run(
        "api.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="warning" if not settings.API_DEBUG else "debug",
        access_log=False,
        log_config=None,
    )
