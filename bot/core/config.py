"""
机器人核心配置模块

该模块定义了机器人运行所需的所有配置类, 包括:
- 机器人基础配置
- 数据库配置
- API 服务配置
"""

from __future__ import annotations
import contextlib
import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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
    OWNER_ID: int = Field(..., description="所有者用户ID（唯一，必填）")
    ADMIN_IDS: str = Field(default="", description="管理员ID列表（逗号分隔）")
    GROUP: str | None = Field(default=None, description="绑定的群组Username或ID")
    PROJECT_NAME: str = Field(default="", description="项目名称，用于日志与Banner")
    EMBY_BASE_URL: str | None = Field(default=None, description="Emby 服务地址, 例如 https://your-emby.com")
    EMBY_PORT: int = Field(default=443, description="Emby 端口，默认 443（https）或 80（http）")
    EMBY_API_KEY: str | None = Field(default=None, description="Emby API Key, 通过 X-Emby-Token 传递")
    EMBY_TEMPLATE_USER_ID: str | None = Field(default=None, description="Emby 模板用户ID，用于创建用户时复制配置")
    EMBY_API_PREFIX: str | None = Field(default="/emby", description="Emby API 路径前缀, 例如 /emby; 可为空")
    NOTIFICATION_CHANNEL_ID: str | None = Field(default=None, description="通知频道ID列表，逗号分隔，支持Username(@channel)或数字ID")

    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if ":" not in v:
            msg = "BOT_TOKEN 格式不正确，必须包含 ':'"
            raise ValueError(msg)
        return v

    @field_validator("ADMIN_IDS")
    @classmethod
    def validate_admin_ids(cls, v: str) -> str:
        if not v:
            return v
        ids = [x.strip() for x in v.split(",") if x.strip()]
        if not all(x.isdigit() for x in ids):
            msg = "ADMIN_IDS 必须全为数字，用逗号分隔"
            raise ValueError(msg)
        return v

    @field_validator("EMBY_BASE_URL")
    @classmethod
    def validate_emby_base_url(cls, v: str | None) -> str | None:
        """校验 Emby 基础地址

        功能说明:
        - 确保 `EMBY_BASE_URL` 以 http/https 开头, 为空时允许

        输入参数:
        - v: 环境变量读取到的字符串或 None

        返回值:
        - str | None: 合法的地址或 None
        """
        if v is None or not v.strip():
            return None
        s = v.strip()
        if not (s.startswith(("http://", "https://"))):
            msg = "EMBY_BASE_URL 必须以 http:// 或 https:// 开头"
            raise ValueError(msg)
        return s.rstrip("/")

    def get_emby_base_url(self) -> str | None:
        """获取 Emby 基础地址

        功能说明:
        - 返回配置中的 `EMBY_BASE_URL`, 若未设置返回 None

        输入参数:
        - 无

        返回值:
        - str | None: Emby 服务地址
        """
        return self.EMBY_BASE_URL

    def get_emby_api_key(self) -> str | None:
        """获取 Emby API Key

        功能说明:
        - 返回配置中的 `EMBY_API_KEY`, 若未设置返回 None

        输入参数:
        - 无

        返回值:
        - str | None: Emby API Key
        """
        return self.EMBY_API_KEY

    @field_validator("EMBY_API_PREFIX")
    @classmethod
    def validate_emby_api_prefix(cls, v: str | None) -> str | None:
        """校验 Emby API 路径前缀

        功能说明:
        - 允许为空或以 `/` 开头的简短路径, 自动去除末尾的 `/`

        输入参数:
        - v: 环境变量读取到的字符串或 None

        返回值:
        - str | None: 规范化后的前缀或 None
        """
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if not s.startswith("/"):
            s = "/" + s
        return s.rstrip("/")

    def get_emby_api_prefix(self) -> str | None:
        """获取 Emby API 路径前缀

        功能说明:
        - 返回配置中的 `EMBY_API_PREFIX`, 若为空返回 None

        输入参数:
        - 无

        返回值:
        - str | None: 路径前缀, 例如 "/emby" 或 None
        """
        return self.EMBY_API_PREFIX

    def has_emby_config(self) -> bool:
        """判断是否已配置 Emby 连接信息

        功能说明:
        - 确认 `EMBY_BASE_URL` 与 `EMBY_API_KEY` 同时存在

        输入参数:
        - 无

        返回值:
        - bool: 是否已配置
        """
        return bool(self.EMBY_BASE_URL and self.EMBY_API_KEY)

    def get_emby_template_user_id(self) -> str | None:
        """获取 Emby 模板用户ID

        功能说明:
        - 返回配置中的 `EMBY_TEMPLATE_USER_ID`, 若未设置返回 None

        输入参数:
        - 无

        返回值:
        - str | None: 模板用户ID
        """
        v = self.EMBY_TEMPLATE_USER_ID
        if v is None:
            return None
        s = v.strip()
        return s or None

    def get_notification_channel_ids(self) -> list[str | int]:
        """获取通知频道ID列表

        功能说明:
        - 解析 `NOTIFICATION_CHANNEL_ID` 为 ID 列表
        - 支持逗号分隔
        - 尝试将数字字符串转换为 int

        输入参数:
        - 无

        返回值:
        - list[str | int]: 频道ID列表
        """
        v = self.NOTIFICATION_CHANNEL_ID
        if not v:
            return []

        # 如果已经是 int (虽然 Field 定义改为了 str | None，但为了稳健性)
        if isinstance(v, int):
            return [v]

        results = []
        parts = [x.strip() for x in str(v).split(",") if x.strip()]
        for p in parts:
            # 尝试转换为 int
            try:
                results.append(int(p))
            except ValueError:
                results.append(p)
        return results

    def get_owner_id(self) -> int:
        """获取所有者用户ID

        功能说明:
        - 返回配置中的 `OWNER_ID`

        输入参数:
        - 无

        返回值:
        - int: 所有者用户ID
        """
        return int(self.OWNER_ID)

    def get_admin_ids(self) -> list[int]:
        """获取管理员用户ID列表

        功能说明:
        - 解析 `ADMIN_IDS` 为整数列表

        输入参数:
        - 无

        返回值:
        - list[int]: 管理员ID列表
        """
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]


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
    @classmethod
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

    TIMEZONE: str = Field(default="UTC", description="应用时区名称或偏移, 例如 'Asia/Shanghai' 或 '+08:00'")

    @model_validator(mode="after")
    def validate_all(self) -> Settings:
        if not self.DB_NAME:
            msg = "数据库名称 DB_NAME 不能为空"
            raise ValueError(msg)
        # 强制要求 OWNER_ID 存在或可回退
        _ = self.get_owner_id()
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

    def get_timezone_name(self) -> str:
        """
        获取应用时区名称字符串

        功能说明:
        - 返回环境变量配置的时区字符串, 支持 'Asia/Shanghai' 或 '+08:00'

        输入参数:
        - 无

        返回值:
        - str: 时区名称或偏移字符串
        """
        return (self.TIMEZONE or "UTC").strip() or "UTC"

    def get_timezone_offset_str(self) -> str:
        """
        获取应用时区的偏移字符串

        功能说明:
        - 若 `TIMEZONE` 为偏移字符串(如 '+08:00')则直接返回
        - 若为名称(如 'Asia/Shanghai'), 通过 ZoneInfo 计算当前偏移

        输入参数:
        - 无

        返回值:
        - str: 形如 '+HH:MM' 或 '-HH:MM' 的偏移字符串
        """
        tz = self.get_timezone_name()
        s = tz.upper()
        if s in {"Z", "UTC"}:
            return "+00:00"
        if re.match(r"^[+-]\\d{2}:\\d{2}$", tz):
            return tz
        with contextlib.suppress(Exception):
            zi = ZoneInfo(tz)
            now = _dt.datetime.now(zi)
            offset = now.utcoffset() or _dt.timedelta(0)
            total = int(offset.total_seconds())
            sign = "+" if total >= 0 else "-"
            total_abs = abs(total)
            hours, rem = divmod(total_abs, 3600)
            minutes = rem // 60
            return f"{sign}{hours:02d}:{minutes:02d}"
        # 常见时区名称的固定偏移回退
        name_offsets = {
            "Asia/Shanghai": "+08:00",
            "Asia/Chongqing": "+08:00",
            "Asia/Harbin": "+08:00",
            "Asia/Urumqi": "+08:00",
            "Asia/Hong_Kong": "+08:00",
            "Asia/Taipei": "+08:00",
            "Asia/Singapore": "+08:00",
        }
        return name_offsets.get(tz, "+00:00")


settings = Settings()
