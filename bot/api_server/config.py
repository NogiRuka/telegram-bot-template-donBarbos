"""
API服务配置
复用bot项目的数据库配置，添加API服务特有的配置
"""
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.core.config import settings as bot_settings


class APISettings(BaseSettings):
    """
    API服务配置类

    复用bot的数据库配置，添加API服务特有的配置。所有字段支持通过 .env 配置，
    并兼容 `API_` 前缀与无前缀两种环境变量命名方式。
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 服务器配置（支持 API_HOST/HOST 等别名）
    HOST: str = Field(
        "0.0.0.0",
        validation_alias=AliasChoices("API_HOST", "HOST"),
        description="API 服务监听主机",
    )
    PORT: int = Field(
        8000,
        validation_alias=AliasChoices("API_PORT", "PORT"),
        description="API 服务监听端口",
    )
    DEBUG: bool = Field(
        True,
        validation_alias=AliasChoices("API_DEBUG", "DEBUG"),
        description="API 调试模式开关",
    )

    # CORS 配置（支持逗号分隔字符串或 JSON 数组）
    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        validation_alias=AliasChoices("API_ALLOWED_ORIGINS", "ALLOWED_ORIGINS"),
        description="允许跨域的来源列表",
    )

    # 安全配置
    SECRET_KEY: str = Field(
        "请在此处设置您的密钥",
        validation_alias=AliasChoices("API_SECRET_KEY", "SECRET_KEY"),
        description="API 服务密钥",
    )
    # Emby Webhook 简单鉴权令牌（可选）。如果设置，则必须匹配。
    EMBY_WEBHOOK_TOKEN: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBY_WEBHOOK_TOKEN", "API_EMBY_WEBHOOK_TOKEN"),
        description="Emby Webhook 鉴权令牌",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    def parse_allowed_origins(self, v: Any) -> list[str]:
        """解析允许的跨域来源列表

        功能说明：
        - 支持从逗号分隔字符串或 JSON 数组字符串解析为列表

        输入参数：
        - v: 任意类型的原始输入值

        返回值：
        - List[str]: 解析后的字符串列表
        """
        try:
            if v is None:
                return []
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    return []
                if s.startswith("[") and s.endswith("]"):
                    import json

                    arr = json.loads(s)
                    return [str(x).strip() for x in arr if str(x).strip()]
                return [x.strip() for x in s.split(",") if x.strip()]
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            return []
        except Exception:
            return []

    # 复用 bot 的数据库配置
    @property
    def database_url(self) -> str:
        """获取数据库连接URL

        功能说明：
        - 复用 bot 核心配置中的数据库连接字符串

        输入参数：
        - 无

        返回值：
        - str: 数据库连接 URL 字符串
        """
        return bot_settings.database_url


# 创建配置实例
settings = APISettings()
