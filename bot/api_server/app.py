"""
API服务主应用
独立的 FastAPI 应用, 为 React 前端提供数据接口
位于 bot 目录下, 可直接调用 bot 的数据库操作
"""
from __future__ import annotations
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from bot.api_server.config import settings
from bot.api_server.routes import admins, dashboard, users, webhooks

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
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
    yield
    logger.info("API 服务关闭中...")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 配置好的FastAPI应用实例
    """
    app = FastAPI(
        title="Telegram Bot Admin API",
        description="为Telegram Bot管理界面提供的API服务",
        version="1.0.0",
        lifespan=lifespan
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
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


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    logger.info(f"启动API服务在 http://{settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "bot.api_server.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=False,
    )
