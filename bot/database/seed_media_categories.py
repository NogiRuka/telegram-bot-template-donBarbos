"""
媒体库分类数据初始化脚本

功能说明:
- 初始化默认媒体库分类数据
- 支持分类的启用/禁用和排序
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import select

from bot.database.models.media_category import MediaCategoryModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def init_media_categories(session: AsyncSession) -> None:
    """初始化媒体库分类数据

    功能说明:
    - 检查是否已存在分类数据
    - 如果不存在，创建默认分类

    输入参数:
    - session: 异步数据库会话

    返回值:
    - None
    """
    # 检查是否已存在数据
    result = await session.execute(select(MediaCategoryModel))
    existing_count = len(result.scalars().all())

    if existing_count > 0:
        return  # 已有数据，跳过初始化

    # 默认分类数据
    default_categories = [
        {"name": "电影", "description": "院线电影、网络电影等", "sort_order": 1},
        {"name": "剧集", "description": "电视剧、网剧等连续剧集", "sort_order": 2},
        {"name": "动漫", "description": "动画片、动漫剧集等", "sort_order": 3},
        {"name": "国产", "description": "国产成人内容", "sort_order": 4},
        {"name": "日韩", "description": "日韩成人内容", "sort_order": 5},
        {"name": "欧美", "description": "欧美成人内容", "sort_order": 6},
    ]

    # 创建分类数据
    for category_data in default_categories:
        category = MediaCategoryModel(
            name=category_data["name"],
            description=category_data["description"],
            is_enabled=True,
            sort_order=category_data["sort_order"]
        )
        session.add(category)

    await session.commit()


async def get_enabled_categories(session: AsyncSession) -> list[str]:
    """获取启用的分类列表

    功能说明:
    - 查询所有启用的分类
    - 按排序顺序返回分类名称列表

    输入参数:
    - session: 异步数据库会话

    返回值:
    - list[str]: 启用的分类名称列表
    """
    result = await session.execute(
        select(MediaCategoryModel)
        .where(MediaCategoryModel.is_enabled)
        .order_by(MediaCategoryModel.sort_order)
    )
    categories = result.scalars().all()
    return [category.name for category in categories]
