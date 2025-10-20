"""
API服务主应用
独立的FastAPI应用，为React前端提供数据接口
现在位于bot目录下，可以直接调用bot的数据库操作
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from bot.api_server.routes import dashboard, users, admins
from bot.api_server.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    Args:
        app: FastAPI应用实例
    """
    logger.info("API服务启动中...")
    yield
    logger.info("API服务关闭中...")


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
    
    @app.get("/")
    async def root():
        """
        根路径健康检查
        
        Returns:
            dict: 服务状态信息
        """
        return {"message": "Telegram Bot Admin API", "status": "running"}
    
    @app.get("/health")
    async def health_check():
        """
        健康检查端点
        
        Returns:
            dict: 健康状态信息
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
        log_level="info" if not settings.DEBUG else "debug"
    )