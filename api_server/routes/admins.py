"""
管理员API路由
提供管理员数据接口（模拟数据）
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


class AdminResponse(BaseModel):
    """管理员响应模型"""
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: str
    updated_at: str
    roles: List[str]


class AdminsListResponse(BaseModel):
    """管理员列表响应模型"""
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
    获取管理员列表（模拟数据）
    
    Args:
        page: 页码
        per_page: 每页数量
        
    Returns:
        AdminsListResponse: 管理员列表数据
    """
    try:
        # 模拟管理员数据
        admins_data = [
            AdminResponse(
                id=1,
                email="admin@example.com",
                first_name="管理员",
                last_name="",
                is_active=True,
                created_at=(datetime.now() - timedelta(days=30)).isoformat(),
                updated_at=datetime.now().isoformat(),
                roles=["superuser"]
            ),
            AdminResponse(
                id=2,
                email="moderator@example.com",
                first_name="版主",
                last_name="",
                is_active=True,
                created_at=(datetime.now() - timedelta(days=15)).isoformat(),
                updated_at=datetime.now().isoformat(),
                roles=["moderator"]
            )
        ]
        
        # 简单分页处理
        total = len(admins_data)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_data = admins_data[start_idx:end_idx]
        
        return AdminsListResponse(
            items=paginated_data,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
        
    except Exception as e:
        logger.error(f"获取管理员列表失败: {e}")
        return AdminsListResponse(
            items=[],
            total=0,
            page=page,
            per_page=per_page,
            pages=0
        )


@router.get("/admins/{admin_id}", response_model=AdminResponse)
async def get_admin_detail(admin_id: int):
    """
    获取管理员详情（模拟数据）
    
    Args:
        admin_id: 管理员ID
        
    Returns:
        AdminResponse: 管理员详情数据
    """
    try:
        # 模拟数据
        if admin_id == 1:
            return AdminResponse(
                id=1,
                email="admin@example.com",
                first_name="管理员",
                last_name="",
                is_active=True,
                created_at=(datetime.now() - timedelta(days=30)).isoformat(),
                updated_at=datetime.now().isoformat(),
                roles=["superuser"]
            )
        elif admin_id == 2:
            return AdminResponse(
                id=2,
                email="moderator@example.com",
                first_name="版主",
                last_name="",
                is_active=True,
                created_at=(datetime.now() - timedelta(days=15)).isoformat(),
                updated_at=datetime.now().isoformat(),
                roles=["moderator"]
            )
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="管理员不存在")
            
    except Exception as e:
        logger.error(f"获取管理员详情失败: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="获取管理员详情失败")