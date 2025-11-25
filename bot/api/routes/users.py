"""
用户管理API路由
提供用户数据管理接口, 调用 bot 的数据库操作服务
"""
from __future__ import annotations
from typing import Annotated, NoReturn

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from bot.database.database import sessionmaker
from bot.database.models import UserModel
from bot.services.users import get_user_count, user_exists

router = APIRouter()


class UserResponse(BaseModel):
    """
    用户响应模型（与《设计文档》users 表一致）

    Attributes:
        id: 用户的 Telegram ID, 主键
        is_bot: 是否机器人
        first_name: 用户的名字
        last_name: 用户的姓氏
        username: 用户名
        language_code: 用户语言代码
        is_premium: 是否 Premium 用户
        added_to_attachment_menu: 是否加入附件菜单
        remark: 备注
        created_at: 创建时间
        created_by: 创建者ID
        updated_at: 更新时间
        updated_by: 更新者ID
        is_deleted: 是否删除
        deleted_at: 删除时间
        deleted_by: 删除者ID
    """
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool | None
    added_to_attachment_menu: bool | None
    remark: str | None
    created_at: str
    created_by: int | None
    updated_at: str
    updated_by: int | None
    is_deleted: bool
    deleted_at: str | None
    deleted_by: int | None


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
    items: list[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/users", response_model=UsersListResponse)
async def get_users_list(
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 10,
    search: Annotated[str | None, Query(description="搜索关键词")] = None,
    sort_by: Annotated[str | None, Query(description="排序字段")] = "created_at",
    sort_order: Annotated[str, Query(description="排序方向 (asc/desc)")] = "desc"
) -> UsersListResponse:
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

            # 构建查询
            query = select(UserModel)
            count_query = select(func.count(UserModel.id))

            # 搜索过滤
            if search:
                search_filter = or_(
                    UserModel.username.ilike(f"%{search}%"),
                    UserModel.first_name.ilike(f"%{search}%"),
                    UserModel.last_name.ilike(f"%{search}%")
                )
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)

            # 获取总数
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # 排序处理
            valid_sort_fields = {
                "id": UserModel.id,
                "first_name": UserModel.first_name,
                "last_name": UserModel.last_name,
                "username": UserModel.username,
                "created_at": UserModel.created_at,
                "updated_at": UserModel.updated_at,
                "is_premium": UserModel.is_premium,
            }

            # 验证排序字段
            if sort_by not in valid_sort_fields:
                sort_by = "created_at"

            # 验证排序方向
            if sort_order.lower() not in ["asc", "desc"]:
                sort_order = "desc"

            # 应用排序
            sort_column = valid_sort_fields[sort_by]
            if sort_order.lower() == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # 分页查询
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

            result = await session.execute(query)
            users = result.scalars().all()

            # 转换为响应模型
            users_data = [
                UserResponse(
                    id=u.id,
                    is_bot=u.is_bot,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    username=u.username,
                    language_code=u.language_code,
                    is_premium=u.is_premium,
                    added_to_attachment_menu=u.added_to_attachment_menu,
                    remark=u.remark,
                    created_at=u.created_at.isoformat() if u.created_at else None,
                    created_by=u.created_by,
                    updated_at=u.updated_at.isoformat() if u.updated_at else None,
                    updated_by=u.updated_by,
                    is_deleted=u.is_deleted,
                    deleted_at=u.deleted_at.isoformat() if u.deleted_at else None,
                    deleted_by=u.deleted_by,
                )
                for u in users
            ]

            # 计算总页数
            pages = (total + per_page - 1) // per_page

            return UsersListResponse(
                items=users_data,
                total=total,
                page=page,
                per_page=per_page,
                pages=pages
            )

    except Exception as err:
        logger.error(f"获取用户列表失败: {err}")
        raise HTTPException(status_code=500, detail="获取用户列表失败") from err


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(user_id: int) -> UserResponse:
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
                raise_user_not_found()

            query = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise_user_not_found()

            return UserResponse(
                id=user.id,
                is_bot=user.is_bot,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                language_code=user.language_code,
                is_premium=user.is_premium,
                added_to_attachment_menu=user.added_to_attachment_menu,
                remark=user.remark,
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
    except Exception as err:
        logger.error(f"获取用户详情失败: {err}")
        raise HTTPException(status_code=500, detail="获取用户详情失败") from err


@router.get("/users/stats/count")
async def get_users_count() -> dict[str, int]:
    """
    获取用户总数统计

    Returns:
        dict: 用户总数信息
    """
    try:
        async with sessionmaker() as session:
            total = await get_user_count(session)
            return {"total_users": total}

    except Exception as err:
        logger.error(f"获取用户统计失败: {err}")
        raise HTTPException(status_code=500, detail="获取用户统计失败") from err
def raise_user_not_found() -> NoReturn:
    """
    抛出404

    功能说明:
    - 用户不存在时抛出 HTTP 404

    输入参数:
    - 无

    返回值:
    - None
    """
    raise HTTPException(status_code=404, detail="用户不存在")
