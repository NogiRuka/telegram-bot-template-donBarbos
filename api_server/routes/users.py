"""
用户管理API路由
提供用户数据管理接口
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from bot.database.database import sessionmaker
from bot.database.models import UserModel

router = APIRouter()


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str]
    is_premium: Optional[bool]
    created_at: Optional[str]
    updated_at: Optional[str]


class UsersListResponse(BaseModel):
    """用户列表响应模型"""
    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/users", response_model=UsersListResponse)
async def get_users_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """
    获取用户列表
    
    Args:
        page: 页码
        per_page: 每页数量
        search: 搜索关键词
        
    Returns:
        UsersListResponse: 用户列表数据
    """
    try:
        async with sessionmaker() as session:
            from sqlalchemy import select, func, or_
            
            # 构建查询
            query = select(UserModel)
            count_query = select(func.count(UserModel.user_id))
            
            # 搜索过滤
            if search:
                search_filter = or_(
                    UserModel.username.ilike(f'%{search}%'),
                    UserModel.first_name.ilike(f'%{search}%'),
                    UserModel.last_name.ilike(f'%{search}%')
                )
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)
            
            # 获取总数
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0
            
            # 分页查询
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page).order_by(UserModel.created_at.desc())
            
            result = await session.execute(query)
            users = result.scalars().all()
            
            # 转换为响应模型
            users_data = []
            for user in users:
                users_data.append(UserResponse(
                    id=user.user_id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=user.language_code,
                    is_premium=user.is_premium,
                    created_at=user.created_at.isoformat() if user.created_at else None,
                    updated_at=user.updated_at.isoformat() if user.updated_at else None,
                ))
            
            return UsersListResponse(
                items=users_data,
                total=total,
                page=page,
                per_page=per_page,
                pages=(total + per_page - 1) // per_page
            )
            
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户列表失败")


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(user_id: int):
    """
    获取用户详情
    
    Args:
        user_id: 用户ID
        
    Returns:
        UserResponse: 用户详情数据
    """
    try:
        async with sessionmaker() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(UserModel).where(UserModel.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            return UserResponse(
                id=user.user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                is_premium=user.is_premium,
                created_at=user.created_at.isoformat() if user.created_at else None,
                updated_at=user.updated_at.isoformat() if user.updated_at else None,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户详情失败")