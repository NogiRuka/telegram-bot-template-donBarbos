#!/usr/bin/env python3
"""
API服务启动脚本
独立启动FastAPI服务，为React前端提供数据接口
现在API服务位于bot目录下，可以直接调用bot的数据库操作
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    from bot.api_server.app import app
    from bot.api_server.config import settings
    
    print(f"🚀 启动API服务...")
    print(f"📍 地址: http://{settings.HOST}:{settings.PORT}")
    print(f"🔧 调试模式: {'开启' if settings.DEBUG else '关闭'}")
    print(f"🌐 允许的来源: {', '.join(settings.ALLOWED_ORIGINS)}")
    print(f"🗄️ 数据库: {settings.database_url}")
    print("=" * 50)
    
    uvicorn.run(
        "bot.api_server.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )