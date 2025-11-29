"""API 应用模块

功能说明:
- 构建并导出 FastAPI 应用实例, 供 `uvicorn` 或 `python -m bot.api` 使用

依赖安装(Windows):
- pip install fastapi loguru
"""

from __future__ import annotations
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from bot.api.routes import admins, dashboard, users, webhooks
from bot.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable


@asynccontextmanager
async def api_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """API 生命周期事件处理

    功能说明:
    - 在应用启动前后输出提示日志, 覆盖完整生命周期

    输入参数:
    - app: FastAPI 应用实例

    返回值:
    - None
    """
    del app
    logger.info("🚀 API 服务启动中...")
    logger.info("✅ API 服务启动完成")
    yield
    logger.info("⏹️ API 服务停止中...")
    logger.info("✅ API 服务已停止")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例

    功能说明:
    - 配置应用元信息与 CORS
    - 注册核心路由与健康检查

    输入参数:
    - 无

    返回值:
    - FastAPI: 已配置的应用实例
    """
    app = FastAPI(
        title="Telegram Bot Admin API",
        description="为 Telegram Bot 管理界面提供的 API 服务",
        version="1.0.0",
        lifespan=api_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_api_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(users.router, prefix="/api", tags=["users"])
    app.include_router(admins.router, prefix="/api", tags=["admins"])
    app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
    app.add_api_route("/", webhooks.handle_emby_webhook, methods=["POST"], tags=["webhooks"])

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """请求日志中间件

        功能说明:
        - 记录每次请求的方法、路径、状态码、耗时与客户端IP

        输入参数:
        - request: FastAPI 请求对象
        - call_next: 下游处理器

        返回值:
        - Response: FastAPI 响应对象
        """
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = getattr(response, "status_code", 0)
        except Exception as err:
            duration_ms = int((time.perf_counter() - start) * 1000)
            client_ip = request.client.host if request.client else "-"
            logger.error(
                "⛔ API {method} {path} -> EXC {ms}ms from {client}: {err}",
                method=request.method,
                path=request.url.path,
                ms=duration_ms,
                client=client_ip,
                err=err,
            )
            raise
        else:
            duration_ms = int((time.perf_counter() - start) * 1000)
            client_ip = request.client.host if request.client else "-"
            logger.info(
                "📥 API {method} {path} -> {status} {ms}ms from {client}",
                method=request.method,
                path=request.url.path,
                status=status,
                ms=duration_ms,
                client=client_ip,
            )
            return response

    @app.get("/")
    async def root() -> dict[str, str]:
        """根路径健康检查

        功能说明:
        - 返回服务运行状态信息

        输入参数:
        - 无

        返回值:
        - dict[str, str]: 服务状态信息
        """
        return {"message": "Telegram Bot Admin API", "status": "running"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """健康检查端点

        功能说明:
        - 返回健康状态信息

        输入参数:
        - 无

        返回值:
        - dict[str, str]: 健康状态信息
        """
        return {"status": "healthy"}

    return app


# 导出应用实例
app = create_app()
