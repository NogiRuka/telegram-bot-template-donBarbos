"""
API服务配置
"""
from __future__ import annotations
import os
from typing import List

from pydantic import BaseSettings


class APISettings(BaseSettings):
    """API服务配置类"""
    
    # 服务器配置
    HOST: str = "localhost"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React开发服务器
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    
    # 数据库配置（复用bot项目的配置）
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bot.db")
    
    # Redis配置（复用bot项目的配置）
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建配置实例
settings = APISettings()