from __future__ import annotations
import contextlib
from typing import TYPE_CHECKING, Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bot.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.engine.url import URL


def _configure_mysql_shanghai_tz(engine: AsyncEngine) -> None:
    """
    设置数据库会话时区为环境变量指定的时区

    功能说明:
    - 针对 MySQL 驱动设置每个连接的 `time_zone`
    - 支持偏移字符串(如 '+08:00')与 IANA 名称(如 'Asia/Shanghai')

    输入参数:
    - engine: 异步数据库引擎

    返回值:
    - None
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
        tzname = settings.get_timezone_name()
        with contextlib.suppress(Exception):
            cursor = dbapi_connection.cursor()
            cursor.execute(f"SET time_zone = '{tzname}'")
            cursor.close()
        with contextlib.suppress(Exception):
            cursor = dbapi_connection.cursor()
            tzoffset = settings.get_timezone_offset_str()
            cursor.execute(f"SET time_zone = '{tzoffset}'")
            cursor.close()


def get_engine(url: URL | str = settings.database_url, echo: bool = False) -> AsyncEngine:
    """
    创建异步数据库引擎

    功能说明:
    - 创建并返回 SQLAlchemy 异步引擎
    - 注册连接事件, 将 MySQL 会话时区设置为上海

    输入参数:
    - url: 数据库连接URL
    - echo: 是否回显执行的SQL语句 (默认 False)

    返回值:
    - AsyncEngine: 异步数据库引擎
    """
    engine = create_async_engine(
        url=url,
        echo=echo,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )
    _configure_mysql_shanghai_tz(engine)
    return engine


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    创建异步会话工厂

    功能说明:
    - 使用指定引擎创建会话工厂, 关闭自动刷新与提交过期

    输入参数:
    - engine: 异步数据库引擎

    返回值:
    - async_sessionmaker[AsyncSession]: 异步会话工厂
    """
    return async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


db_url = settings.database_url
engine = get_engine(url=db_url, echo=settings.DB_ECHO)
sessionmaker = get_sessionmaker(engine)
