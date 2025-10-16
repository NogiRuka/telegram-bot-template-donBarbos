from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bot.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.engine.url import URL


def get_engine(url: URL | str = settings.database_url) -> AsyncEngine:
    """
    创建异步数据库引擎
    
    Args:
        url: 数据库连接URL
        
    Returns:
        AsyncEngine: 异步数据库引擎
    """
    return create_async_engine(
        url=url,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    创建异步会话工厂
    
    Args:
        engine: 异步数据库引擎
        
    Returns:
        async_sessionmaker[AsyncSession]: 异步会话工厂
    """
    return async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


db_url = settings.database_url
engine = get_engine(url=db_url)
sessionmaker = get_sessionmaker(engine)
