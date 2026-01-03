from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import MediaCategoryModel

if TYPE_CHECKING:
    from bot.database.models import MediaCategoryModel as MediaCategoryModelType


class SubmissionParseError(Exception):
    """投稿解析错误"""
    pass


async def parse_request_input(session: AsyncSession, text: str) -> dict:
    """解析用户求片输入
    
    功能说明:
    - 解析用户输入的求片信息
    - 验证分类ID的有效性
    - 返回标准化的数据结构
    
    输入参数:
    - session: 数据库会话
    - text: 用户输入的文本
    
    返回值:
    - dict: 包含title, category_id, category_name, description等字段
    
    异常:
    - SubmissionParseError: 当输入格式不正确时抛出
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        raise SubmissionParseError("请输入内容")
    
    # 解析标题（必填）
    title = lines[0]
    if not title or len(title) > 255:
        raise SubmissionParseError("标题不能为空且不能超过255字符")
    
    # 解析分类ID（必填）
    category_id = None
    category_name = ""
    
    if len(lines) >= 2:
        try:
            category_id = int(lines[1])
            # 验证分类是否存在且启用
            stmt = select(MediaCategoryModel).where(
                MediaCategoryModel.id == category_id,
                MediaCategoryModel.is_enabled == True,
                MediaCategoryModel.is_deleted == False
            )
            result = await session.execute(stmt)
            category = result.scalar_one_or_none()
            
            if not category:
                raise SubmissionParseError(f"分类ID {category_id} 不存在或未启用")
            
            category_name = category.name
            
        except ValueError:
            raise SubmissionParseError("分类ID必须是数字")
    else:
        # 如果没有提供分类ID，使用默认分类
        stmt = select(MediaCategoryModel).where(
            MediaCategoryModel.is_enabled == True,
            MediaCategoryModel.is_deleted == False
        ).order_by(MediaCategoryModel.sort_order.asc())
        
        result = await session.execute(stmt)
        category = result.scalar_one_or_none()
        
        if not category:
            raise SubmissionParseError("暂无可用的分类")
        
        category_id = category.id
        category_name = category.name
    
    # 解析描述（可选）
    description = ""
    if len(lines) >= 3:
        description = lines[2]
    
    # 解析其他备注（可选）
    if len(lines) >= 4:
        description += f"\n\n备注：{lines[3]}"
    
    return {
        "title": title,
        "category_id": category_id,
        "category_name": category_name,
        "description": description.strip()
    }


async def parse_submit_input(session: AsyncSession, text: str) -> dict:
    """解析用户投稿输入
    
    功能说明:
    - 解析用户输入的投稿信息
    - 验证分类ID的有效性
    - 返回标准化的数据结构
    
    输入参数:
    - session: 数据库会话
    - text: 用户输入的文本
    
    返回值:
    - dict: 包含title, category_id, category_name, description等字段
    
    异常:
    - SubmissionParseError: 当输入格式不正确时抛出
    """
    # 投稿的解析逻辑与求片相同
    return await parse_request_input(session, text)