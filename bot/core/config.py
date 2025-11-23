"""
机器人核心配置模块

该模块定义了机器人运行所需的所有配置类, 包括:
- 机器人基础配置
- 数据库配置
- API 服务配置
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录
DIR = Path(__file__).resolve().parents[2]
# 机器人目录
BOT_DIR = Path(__file__).resolve().parents[1]


class EnvBaseSettings(BaseSettings):
    """基础环境变量设置"""

    model_config = SettingsConfigDict(
        env_file=DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


class BotSettings(EnvBaseSettings):
    """机器人基础配置"""

    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    SUPPORT_URL: str | None = None
    RATE_LIMIT: float = Field(default=0.5, description="限流配置，每秒请求数")
    DEBUG: bool = False
    SUPER_ADMIN_IDS: str = Field(default="", description="超级管理员ID列表（逗号分隔）")
    PROJECT_NAME: str = Field(default="", description="项目名称，用于日志与Banner")

    @field_validator("BOT_TOKEN")
    def validate_bot_token(cls, v: str) -> str:
        if ":" not in v:
            msg = "BOT_TOKEN 格式不正确，必须包含 ':'"
            raise ValueError(msg)
        return v

    @field_validator("SUPER_ADMIN_IDS")
    def validate_super_admin_ids(cls, v: str) -> str:
        if not v:
            return v
        ids = [x.strip() for x in v.split(",") if x.strip()]
        if not all(x.isdigit() for x in ids):
            msg = "SUPER_ADMIN_IDS 必须全为数字，用逗号分隔"
            raise ValueError(msg)
        return v

    def get_super_admin_ids(self) -> list[int]:
        if not self.SUPER_ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.SUPER_ADMIN_IDS.split(",") if x.strip()]


class DBSettings(EnvBaseSettings):
    """数据库配置"""

    DB_HOST: str = "localhost"
    DB_PORT: int = Field(default=3306)
    DB_USER: str = "root"
    DB_PASS: str | None = None
    DB_NAME: str = "telegram_bot"

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    @field_validator("DB_PORT")
    def validate_db_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            msg = "数据库端口必须在 1-65535 范围内"
            raise ValueError(msg)
        return v

    @property
    def database_url(self) -> str:
        password = f":{self.DB_PASS}" if self.DB_PASS else ""
        return f"mysql+aiomysql://{self.DB_USER}{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def database_url_pymysql(self) -> str:
        password = f":{self.DB_PASS}" if self.DB_PASS else ""
        return f"mysql+pymysql://{self.DB_USER}{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class APIMixin(EnvBaseSettings):
    """API 服务配置"""

    API_HOST: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("API_HOST", "HOST"),
    )

    API_PORT: int = Field(
        default=8000,
        validation_alias=AliasChoices("API_PORT", "PORT"),
    )

    API_DEBUG: bool = True

    API_ALLOWED_ORIGINS_RAW: str | list[str] | None = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        validation_alias=AliasChoices("API_ALLOWED_ORIGINS", "ALLOWED_ORIGINS"),
    )

    def get_api_allowed_origins(self) -> list[str]:
        raw = self.API_ALLOWED_ORIGINS_RAW
        if raw is None:
            return []

        if isinstance(raw, list):
            return [x.strip() for x in raw if str(x).strip()]

        s = raw.strip()
        if not s:
            return []

        if s.startswith("[") and s.endswith("]"):
            try:
                return [str(x).strip() for x in json.loads(s)]
            except Exception:
                return []

        return [x.strip() for x in s.split(",") if x.strip()]


class Settings(BotSettings, DBSettings, APIMixin):
    """核心主配置"""

    @model_validator(mode="after")
    def validate_all(self) -> Settings:
        if not self.DB_NAME:
            msg = "数据库名称 DB_NAME 不能为空"
            raise ValueError(msg)
        return self

    @property
    def is_production(self) -> bool:
        return not self.DEBUG

    @property
    def is_development(self) -> bool:
        return self.DEBUG

    def get_database_config(self) -> dict[str, Any]:
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }


settings = Settings()
