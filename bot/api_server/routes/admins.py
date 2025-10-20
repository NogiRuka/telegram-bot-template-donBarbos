"""
管理员API路由
提供管理员数据接口，调用bot的数据库操作服务
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from loguru import logger

from bot.database.database import sessionmaker
from bot.database.models import UserModel
from bot.services.users import is_admin, get_all_users

router = APIRouter()


class AdminResponse(BaseModel):
    """
    管理员响应模型
    
    Attributes:
        id: 管理员ID
        username: 用户名
        first_name: 名字
        last_name: 姓氏
        is_active: 是否活跃
        created_at: 创建时间
        updated_at: 更新时间
        roles: 角色列表
    """
    id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    roles: List[str]


class AdminsListResponse(BaseModel):
    """
    管理员列表响应模型
    
    Attributes:
        items: 管理员列表
        total: 总数
        page: 当前页码
        per_page: 每页数量
        pages: 总页数
    """
    items: List[AdminResponse]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/admins", response_model=AdminsListResponse)
async def get_admins_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量")
):
    """
    获取管理员列表
    
    Args:
        page: 页码
        per_page: 每页数量
        
    Returns:
        AdminsListResponse: 管理员列表数据
    """
    try:
        async with sessionmaker() as session:
            from sqlalchemy import select, func
            
            # 获取所有用户，然后筛选管理员
            all_users = await get_all_users(session)
            admin_users = []
            
            for user in all_users:
                if await is_admin(session, user.id):
                    admin_users.append(user)
            
            # 分页处理
            total = len(admin_users)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_admins = admin_users[start_idx:end_idx]
            
            # 转换为响应模型
            admins_data = []
            for admin in paginated_admins:
                # 判断是否活跃（最近7天有活动）
                is_active = True
                if admin.updated_at:
                    week_ago = datetime.now() - timedelta(days=7)
                    is_active = admin.updated_at >= week_ago
                
                admins_data.append(AdminResponse(
                    id=admin.id,
                    username=admin.username,
                    first_name=admin.first_name or "未知",
                    last_name=admin.last_name,
                    is_active=is_active,
                    created_at=admin.created_at.isoformat() if admin.created_at else datetime.now().isoformat(),
                    updated_at=admin.updated_at.isoformat() if admin.updated_at else datetime.now().isoformat(),
                    roles=["admin"]  # 基础角色，可以根据需要扩展
                ))
            
            # 计算总页数
            pages = (total + per_page - 1) // per_page
            
            return AdminsListResponse(
                items=admins_data,
                total=total,
                page=page,
                per_page=per_page,
                pages=pages
            )
            
    except Exception as e:
        logger.error(f"获取管理员列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取管理员列表失败")


@router.get("/admins/{admin_id}", response_model=AdminResponse)
async def get_admin_detail(admin_id: int):
    """
    获取管理员详情
    
    Args:
        admin_id: 管理员ID
        
    Returns:
        AdminResponse: 管理员详情数据
    """
    try:
        async with sessionmaker() as session:
            # 检查是否为管理员
            if not await is_admin(session, admin_id):
                raise HTTPException(status_code=404, detail="管理员不存在")
            
            from sqlalchemy import select
            query = select(UserModel).where(UserModel.id == admin_id)
            result = await session.execute(query)
            admin = result.scalar_one_or_none()
            
            if not admin:
                raise HTTPException(status_code=404, detail="管理员不存在")
            
            # 判断是否活跃
            is_active = True
            if admin.updated_at:
                week_ago = datetime.now() - timedelta(days=7)
                is_active = admin.updated_at >= week_ago
            
            return AdminResponse(
                id=admin.id,
                username=admin.username,
                first_name=admin.first_name or "未知",
                last_name=admin.last_name,
                is_active=is_active,
                created_at=admin.created_at.isoformat() if admin.created_at else datetime.now().isoformat(),
                updated_at=admin.updated_at.isoformat() if admin.updated_at else datetime.now().isoformat(),
                roles=["admin"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取管理员详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取管理员详情失败")


@router.get("/admins/stats/count")
async def get_admins_count():
    """
    获取管理员总数统计
    
    Returns:
        dict: 管理员总数信息
    """
    try:
        async with sessionmaker() as session:
            all_users = await get_all_users(session)
            admin_count = 0
            
            for user in all_users:
                if await is_admin(session, user.id):
                    admin_count += 1
            
            return {"total_admins": admin_count}
            
    except Exception as e:
        logger.error(f"获取管理员统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取管理员统计失败")