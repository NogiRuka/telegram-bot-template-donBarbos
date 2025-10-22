"""
用户管理API路由
提供用户数据管理接口，调用bot的数据库操作服务
"""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from bot.database.database import sessionmaker
from bot.database.models import UserModel
from bot.services.users import get_all_users, get_user_count, user_exists

router = APIRouter()


class UserResponse(BaseModel):
    """
    用户响应模型
    
    Attributes:
        id: 用户ID
        username: 用户名
        first_name: 名字
        last_name: 姓氏
        language_code: 语言代码
        is_premium: 是否为高级用户
        is_admin: 是否为管理员
        is_block: 是否被封禁
        is_suspicious: 是否可疑
        is_bot: 是否为机器人
        message_count: 消息数量
        last_activity_at: 最后活动时间
        created_at: 创建时间
        updated_at: 更新时间
        referrer: 推荐人
        referrer_id: 推荐人ID
        phone_number: 电话号码
        bio: 个人简介
        is_deleted: 是否已删除
        deleted_at: 删除时间
    """
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str]
    is_premium: Optional[bool]
    is_admin: Optional[bool]
    is_block: Optional[bool]
    is_suspicious: Optional[bool]
    is_bot: Optional[bool]
    message_count: Optional[int]
    last_activity_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    referrer: Optional[str]
    referrer_id: Optional[int]
    phone_number: Optional[str]
    bio: Optional[str]
    is_deleted: Optional[bool]
    deleted_at: Optional[str]


class UsersListResponse(BaseModel):
    """
    用户列表响应模型
    
    Attributes:
        items: 用户列表
        total: 总数
        page: 当前页码
        per_page: 每页数量
        pages: 总页数
    """
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
            count_query = select(func.count(UserModel.id))
            
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
                    id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=user.language_code,
                    is_premium=user.is_premium,
                    is_admin=user.is_admin,
                    is_block=user.is_block,
                    is_suspicious=user.is_suspicious,
                    is_bot=user.is_bot,
                    message_count=user.message_count,
                    last_activity_at=user.last_activity_at.isoformat() if user.last_activity_at else None,
                    created_at=user.created_at.isoformat() if user.created_at else None,
                    updated_at=user.updated_at.isoformat() if user.updated_at else None,
                    referrer=user.referrer,
                    referrer_id=user.referrer_id,
                    phone_number=user.phone_number,
                    bio=user.bio,
                    is_deleted=user.is_deleted,
                    deleted_at=user.deleted_at.isoformat() if user.deleted_at else None
                ))
            
            # 计算总页数
            pages = (total + per_page - 1) // per_page
            
            return UsersListResponse(
                items=users_data,
                total=total,
                page=page,
                per_page=per_page,
                pages=pages
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
            # 检查用户是否存在
            if not await user_exists(session, user_id):
                raise HTTPException(status_code=404, detail="用户不存在")
            
            from sqlalchemy import select
            query = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            return UserResponse(
                id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                is_premium=user.is_premium,
                is_admin=user.is_admin,
                is_block=user.is_block,
                is_suspicious=user.is_suspicious,
                is_bot=user.is_bot,
                message_count=user.message_count,
                last_activity_at=user.last_activity_at.isoformat() if user.last_activity_at else None,
                created_at=user.created_at.isoformat() if user.created_at else None,
                updated_at=user.updated_at.isoformat() if user.updated_at else None,
                referrer=user.referrer,
                referrer_id=user.referrer_id,
                phone_number=user.phone_number,
                bio=user.bio,
                is_deleted=user.is_deleted,
                deleted_at=user.deleted_at.isoformat() if user.deleted_at else None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户详情失败")


@router.get("/users/stats/count")
async def get_users_count():
    """
    获取用户总数统计
    
    Returns:
        dict: 用户总数信息
    """
    try:
        async with sessionmaker() as session:
            total = await get_user_count(session)
            return {"total_users": total}
            
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户统计失败")