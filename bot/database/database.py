from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bot.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.engine.url import URL


def get_engine(url: URL | str = settings.database_url, echo: bool = False) -> AsyncEngine:
    """创建异步数据库引擎。

    Args:
        url: 数据库连接 URL。
        echo: 是否在控制台打印执行的 SQL 语句，默认为 False。

    Returns:
        AsyncEngine: SQLAlchemy 异步数据库引擎实例。
    """
    return create_async_engine(
        url=url,
        echo=echo,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """创建异步会话工厂。

    配置说明:
    - autoflush=False: 关闭自动刷新，避免不必要的数据库写入。
    - expire_on_commit=False: 提交后不立即使对象过期，便于在会话关闭后继续访问对象属性。

    Args:
        engine: 异步数据库引擎实例。

    Returns:
        async_sessionmaker[AsyncSession]: 用于创建数据库会话的工厂对象。
    """
    return async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


db_url = settings.database_url
engine = get_engine(url=db_url, echo=settings.DB_ECHO)
sessionmaker = get_sessionmaker(engine)
