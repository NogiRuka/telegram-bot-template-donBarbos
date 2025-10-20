#!/usr/bin/env python3
"""
API服务启动脚本
独立启动FastAPI服务，为React前端提供数据接口
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    from api_server.app import app
    from api_server.config import settings
    
    print(f"🚀 启动API服务...")
    print(f"📍 地址: http://{settings.HOST}:{settings.PORT}")
    print(f"🔧 调试模式: {'开启' if settings.DEBUG else '关闭'}")
    print(f"🌐 允许的来源: {', '.join(settings.ALLOWED_ORIGINS)}")
    print("=" * 50)
    
    uvicorn.run(
        "api_server.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )