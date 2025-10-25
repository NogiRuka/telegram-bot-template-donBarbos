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
    
    按照数据库模型字段顺序定义，与UserModel保持一致
    
    Attributes:
        id: 用户的Telegram ID，主键
        first_name: 用户的名字
        last_name: 用户的姓氏
        username: 用户的Telegram用户名
        phone_number: 用户的电话号码
        bio: 用户的个人简介
        language_code: 用户的语言代码
        last_activity_at: 用户最后活动时间
        is_admin: 是否为管理员
        is_suspicious: 是否可疑用户
        is_block: 是否被封禁
        is_premium: 是否为高级用户
        is_bot: 是否为机器人
        message_count: 消息数量
        created_at: 创建时间
        created_by: 创建者用户ID
        updated_at: 更新时间
        updated_by: 更新者用户ID
        is_deleted: 是否已删除
        deleted_at: 删除时间
        deleted_by: 删除者用户ID
    """
    # 基本身份信息
    id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    
    # 联系方式信息
    phone_number: Optional[str]
    bio: Optional[str]
    language_code: Optional[str]
    
    # 活动时间记录
    last_activity_at: Optional[str]
    
    # 用户状态标志
    is_admin: bool
    is_suspicious: bool
    is_block: bool
    is_premium: bool
    is_bot: bool
    
    # 统计数据
    message_count: int
    
    # 审计字段
    created_at: str
    created_by: Optional[int]
    updated_at: str
    updated_by: Optional[int]
    is_deleted: bool
    deleted_at: Optional[str]
    deleted_by: Optional[int]


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
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向 (asc/desc)")
):
    """
    获取用户列表
    
    Args:
        page: 页码
        per_page: 每页数量
        search: 搜索关键词
        sort_by: 排序字段
        sort_order: 排序方向 (asc/desc)
        
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
            
            # 排序处理
            valid_sort_fields = {
                'id': UserModel.id,
                'first_name': UserModel.first_name,
                'last_name': UserModel.last_name,
                'username': UserModel.username,
                'created_at': UserModel.created_at,
                'updated_at': UserModel.updated_at,
                'last_activity_at': UserModel.last_activity_at,
                'message_count': UserModel.message_count,
                'is_admin': UserModel.is_admin,
                'is_premium': UserModel.is_premium
            }
            
            # 验证排序字段
            if sort_by not in valid_sort_fields:
                sort_by = 'created_at'
            
            # 验证排序方向
            if sort_order.lower() not in ['asc', 'desc']:
                sort_order = 'desc'
            
            # 应用排序
            sort_column = valid_sort_fields[sort_by]
            if sort_order.lower() == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
            
            # 分页查询
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            result = await session.execute(query)
            users = result.scalars().all()
            
            # 转换为响应模型
            users_data = []
            for user in users:
                users_data.append(UserResponse(
                    # 基本身份信息
                    id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=user.username,
                    
                    # 联系方式信息
                    phone_number=user.phone_number,
                    bio=user.bio,
                    language_code=user.language_code,
                    
                    # 活动时间记录
                    last_activity_at=user.last_activity_at.isoformat() if user.last_activity_at else None,
                    
                    # 用户状态标志
                    is_admin=user.is_admin,
                    is_suspicious=user.is_suspicious,
                    is_block=user.is_block,
                    is_premium=user.is_premium,
                    is_bot=user.is_bot,
                    
                    # 统计数据
                    message_count=user.message_count,
                    
                    # 审计字段
                    created_at=user.created_at.isoformat() if user.created_at else None,
                    created_by=user.created_by,
                    updated_at=user.updated_at.isoformat() if user.updated_at else None,
                    updated_by=user.updated_by,
                    is_deleted=user.is_deleted,
                    deleted_at=user.deleted_at.isoformat() if user.deleted_at else None,
                    deleted_by=user.deleted_by
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
                # 基本身份信息
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                
                # 联系方式信息
                phone_number=user.phone_number,
                bio=user.bio,
                language_code=user.language_code,
                
                # 活动时间记录
                last_activity_at=user.last_activity_at.isoformat() if user.last_activity_at else None,
                
                # 用户状态标志
                is_admin=user.is_admin,
                is_suspicious=user.is_suspicious,
                is_block=user.is_block,
                is_premium=user.is_premium,
                is_bot=user.is_bot,
                
                # 统计数据
                message_count=user.message_count,
                
                # 审计字段
                created_at=user.created_at.isoformat() if user.created_at else None,
                created_by=user.created_by,
                updated_at=user.updated_at.isoformat() if user.updated_at else None,
                updated_by=user.updated_by,
                is_deleted=user.is_deleted,
                deleted_at=user.deleted_at.isoformat() if user.deleted_at else None,
                deleted_by=user.deleted_by
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