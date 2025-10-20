"""
API服务配置
复用bot项目的数据库和Redis配置，添加API服务特有的配置
"""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.core.config import settings as bot_settings


class APISettings(BaseSettings):
    """
    API服务配置类
    
    复用bot的数据库和Redis配置，添加API服务特有的配置
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"  # 忽略额外的环境变量
    )
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ]
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    
    # 复用bot的数据库配置
    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        return bot_settings.database_url
    
    @property
    def redis_url(self) -> str:
        """获取Redis连接URL"""
        return bot_settings.redis_url


# 创建配置实例
settings = APISettings()