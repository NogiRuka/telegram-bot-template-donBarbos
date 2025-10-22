"""
机器人核心配置模块

该模块定义了机器人运行所需的所有配置类，包括：
- Webhook 配置
- 机器人基础配置  
- 数据库配置
- 缓存配置
- 外部服务配置
"""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from sqlalchemy.engine.url import URL

# 项目根目录路径
DIR = Path(__file__).absolute().parent.parent.parent
# 机器人代码目录路径
BOT_DIR = Path(__file__).absolute().parent.parent


class EnvBaseSettings(BaseSettings):
    """环境变量基础配置类"""
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore",
        case_sensitive=True
    )


class WebhookSettings(EnvBaseSettings):
    """Webhook 相关配置"""
    # 是否使用 Webhook 模式（生产环境推荐）
    USE_WEBHOOK: bool = False
    # Webhook 基础 URL（需要 HTTPS）
    WEBHOOK_BASE_URL: str = "https://xxx.ngrok-free.app"
    # Webhook 路径
    WEBHOOK_PATH: str = "/webhook"
    # Webhook 密钥（用于验证请求来源）
    WEBHOOK_SECRET: str = ""
    # Webhook 服务器主机
    WEBHOOK_HOST: str = "localhost"
    # Webhook 服务器端口
    WEBHOOK_PORT: int = 8080

    @property
    def webhook_url(self) -> str:
        """获取完整的 Webhook URL"""
        if self.USE_WEBHOOK:
            return f"{self.WEBHOOK_BASE_URL}{self.WEBHOOK_PATH}"
        return f"http://{self.WEBHOOK_HOST}:{self.WEBHOOK_PORT}{self.WEBHOOK_PATH}"

    @validator('WEBHOOK_BASE_URL')
    def validate_webhook_url(cls, v):
        """验证 Webhook URL 格式"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('WEBHOOK_BASE_URL 必须以 http:// 或 https:// 开头')
        return v


class BotSettings(WebhookSettings):
    """机器人基础配置"""
    # Telegram Bot Token（必需）
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    # 支持链接（可选）
    SUPPORT_URL: str | None = None
    # 限流配置（每秒请求数）
    RATE_LIMIT: int | float = Field(default=0.5, description="限流配置，每秒允许的请求数")
    # 调试模式
    DEBUG: bool = False

    @validator('BOT_TOKEN')
    def validate_bot_token(cls, v):
        """验证 Bot Token 格式"""
        if not v:
            raise ValueError('BOT_TOKEN 不能为空')
        if ':' not in v:
            raise ValueError('BOT_TOKEN 格式不正确，应该包含冒号')
        return v


class DBSettings(EnvBaseSettings):
    """数据库配置"""
    # 数据库主机
    DB_HOST: str = "localhost"
    # 数据库端口
    DB_PORT: int = 3306
    # 数据库用户名
    DB_USER: str = "root"
    # 数据库密码
    DB_PASS: str | None = None
    # 数据库名称
    DB_NAME: str = "telegram_bot"
    # 数据库连接池大小
    DB_POOL_SIZE: int = 10
    # 数据库连接池最大溢出数
    DB_MAX_OVERFLOW: int = 20
    # 数据库连接超时时间（秒）
    DB_POOL_TIMEOUT: int = 30

    @property
    def database_url(self) -> str:
        """获取异步数据库连接 URL（用于 aiomysql）"""
        if self.DB_PASS:
            return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return f"mysql+aiomysql://{self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def database_url_pymysql(self) -> str:
        """获取同步数据库连接 URL（用于 pymysql）"""
        if self.DB_PASS:
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return f"mysql+pymysql://{self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @validator('DB_PORT')
    def validate_db_port(cls, v):
        """验证数据库端口范围"""
        if not 1 <= v <= 65535:
            raise ValueError('数据库端口必须在 1-65535 范围内')
        return v


class CacheSettings(EnvBaseSettings):
    """Redis 缓存配置"""
    # Redis 主机
    REDIS_HOST: str = "localhost"
    # Redis 端口
    REDIS_PORT: int = 6379
    # Redis 密码
    REDIS_PASS: str | None = None
    # Redis 数据库编号
    REDIS_DATABASE: int = 0
    # Redis 用户名（Redis 6.0+）
    REDIS_USERNAME: str | None = None
    # FSM 状态缓存过期时间（秒）
    REDIS_TTL_STATE: int = 3600
    # 数据缓存过期时间（秒）
    REDIS_TTL_DATA: int = 1800
    # Redis 连接池大小
    REDIS_POOL_SIZE: int = 10

    @property
    def redis_url(self) -> str:
        """获取 Redis 连接 URL"""
        auth_part = ""
        if self.REDIS_USERNAME and self.REDIS_PASS:
            auth_part = f"{self.REDIS_USERNAME}:{self.REDIS_PASS}@"
        elif self.REDIS_PASS:
            auth_part = f":{self.REDIS_PASS}@"
        
        return f"redis://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DATABASE}"

    @validator('REDIS_PORT')
    def validate_redis_port(cls, v):
        """验证 Redis 端口范围"""
        if not 1 <= v <= 65535:
            raise ValueError('Redis 端口必须在 1-65535 范围内')
        return v

    @validator('REDIS_DATABASE')
    def validate_redis_database(cls, v):
        """验证 Redis 数据库编号"""
        if not 0 <= v <= 15:
            raise ValueError('Redis 数据库编号必须在 0-15 范围内')
        return v


class ExternalServicesSettings(EnvBaseSettings):
    """外部服务配置"""
    # Sentry 错误监控 DSN
    SENTRY_DSN: str | None = None
    # Amplitude 数据分析 API Key
    AMPLITUDE_API_KEY: str = Field(..., description="Amplitude 数据分析 API Key")
    # PostHog 数据分析 API Key
    POSTHOG_API_KEY: str | None = None
    # PostHog 主机地址
    POSTHOG_HOST: str = "https://app.posthog.com"

    @validator('AMPLITUDE_API_KEY')
    def validate_amplitude_key(cls, v):
        """验证 Amplitude API Key"""
        if not v or v.strip() == "":
            raise ValueError('AMPLITUDE_API_KEY 不能为空')
        return v


class Settings(BotSettings, DBSettings, CacheSettings, ExternalServicesSettings):
    """主配置类，整合所有配置"""
    
    def __init__(self, **kwargs):
        """初始化配置，添加验证逻辑"""
        super().__init__(**kwargs)
        self._validate_settings()
    
    def _validate_settings(self):
        """验证配置的一致性"""
        # 如果启用 Webhook，确保 WEBHOOK_BASE_URL 是 HTTPS
        if self.USE_WEBHOOK and not self.WEBHOOK_BASE_URL.startswith('https://'):
            raise ValueError('生产环境的 Webhook 必须使用 HTTPS')
    
    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.DEBUG and self.USE_WEBHOOK
    
    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.DEBUG
    
    def get_database_config(self) -> dict:
        """获取数据库连接配置"""
        return {
            'pool_size': self.DB_POOL_SIZE,
            'max_overflow': self.DB_MAX_OVERFLOW,
            'pool_timeout': self.DB_POOL_TIMEOUT,
            'pool_pre_ping': True,  # 连接前检查连接是否有效
            'pool_recycle': 3600,   # 连接回收时间（秒）
        }
    
    def get_redis_config(self) -> dict:
        """获取 Redis 连接配置"""
        return {
            'host': self.REDIS_HOST,
            'port': self.REDIS_PORT,
            'password': self.REDIS_PASS,
            'db': self.REDIS_DATABASE,
            'username': self.REDIS_USERNAME,
            'max_connections': self.REDIS_POOL_SIZE,
            'retry_on_timeout': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
        }


# 全局配置实例
settings = Settings()
