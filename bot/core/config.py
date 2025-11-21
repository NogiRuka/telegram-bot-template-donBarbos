"""
机器人核心配置模块

该模块定义了机器人运行所需的所有配置类，包括：
- 机器人基础配置
- 数据库配置
- 外部服务配置
"""
from __future__ import annotations
from pathlib import Path

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class BotSettings(EnvBaseSettings):
    """机器人基础配置"""
    # Telegram Bot Token（必需）
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    # 支持链接（可选）
    SUPPORT_URL: str | None = None
    # 限流配置
    RATE_LIMIT: int | float = Field(default=0.5, description="限流配置，每秒允许的请求数")
    # 调试模式
    DEBUG: bool = False
    # 超级管理员ID列表（逗号分隔的字符串）
    SUPER_ADMIN_IDS: str = Field(default="", description="超级管理员ID列表，用逗号分隔")

    @validator("BOT_TOKEN")
    def validate_bot_token(self, v):
        """验证 Bot Token 格式"""
        if not v:
            msg = "BOT_TOKEN 不能为空"
            raise ValueError(msg)
        if ":" not in v:
            msg = "BOT_TOKEN 格式不正确"
            raise ValueError(msg)
        return v

    @validator("SUPER_ADMIN_IDS")
    def validate_super_admin_ids(self, v):
        """验证超级管理员ID格式"""
        if not v:
            return v

        # 分割并验证每个ID
        ids = [id_str.strip() for id_str in v.split(",") if id_str.strip()]
        for id_str in ids:
            try:
                int(id_str)
            except ValueError:
                msg = f"超级管理员ID格式不正确: {id_str}，必须是数字"
                raise ValueError(msg)

        return v

    def get_super_admin_ids(self) -> list[int]:
        """获取超级管理员ID列表"""
        if not self.SUPER_ADMIN_IDS:
            return []

        ids = [id_str.strip() for id_str in self.SUPER_ADMIN_IDS.split(",") if id_str.strip()]
        return [int(id_str) for id_str in ids]


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
    # 是否回显SQL语句（调试用，默认关闭）
    DB_ECHO: bool = False

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

    @validator("DB_PORT")
    def validate_db_port(self, v):
        """验证数据库端口范围"""
        if not 1 <= v <= 65535:
            msg = "数据库端口必须在 1-65535 范围内"
            raise ValueError(msg)
        return v


class Settings(BotSettings, DBSettings):
    """主配置类，整合所有配置"""

    def __init__(self, **kwargs) -> None:
        """初始化配置，添加验证逻辑"""
        super().__init__(**kwargs)
        self._validate_settings()

    def _validate_settings(self) -> None:
        """验证配置的一致性

        功能说明：
        - 对关键配置进行交叉校验，提前发现错误并给出中文提示

        输入参数：
        - 无

        返回值：
        - None
        """
        if not self.BOT_TOKEN or ":" not in self.BOT_TOKEN:
            msg = "BOT_TOKEN 格式不正确，必须包含 ':'"
            raise ValueError(msg)
        if not self.DB_HOST:
            msg = "数据库主机 DB_HOST 不能为空"
            raise ValueError(msg)
        if not self.DB_NAME:
            msg = "数据库名称 DB_NAME 不能为空"
            raise ValueError(msg)

    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.DEBUG

    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.DEBUG

    def get_database_config(self) -> dict:
        """获取数据库连接配置"""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_pre_ping": True,  # 连接前检查连接是否有效
            "pool_recycle": 3600,   # 连接回收时间（秒）
        }


# 全局配置实例
settings = Settings()
