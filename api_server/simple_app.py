"""
简化的API服务
提供模拟数据，不依赖数据库连接
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Dict, Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# 创建FastAPI应用
app = FastAPI(
    title="Telegram Bot Admin API",
    description="为Telegram Bot管理界面提供的API服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 响应模型
class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    is_premium: bool | None
    created_at: str | None
    updated_at: str | None


class UsersListResponse(BaseModel):
    """用户列表响应模型"""
    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


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


# 模拟数据
MOCK_USERS = [
    UserResponse(
        id=1,
        username="user1",
        first_name="张",
        last_name="三",
        language_code="zh",
        is_premium=False,
        created_at=(datetime.now() - timedelta(days=10)).isoformat(),
        updated_at=datetime.now().isoformat()
    ),
    UserResponse(
        id=2,
        username="user2",
        first_name="李",
        last_name="四",
        language_code="zh",
        is_premium=True,
        created_at=(datetime.now() - timedelta(days=5)).isoformat(),
        updated_at=datetime.now().isoformat()
    ),
    UserResponse(
        id=3,
        username="user3",
        first_name="王",
        last_name="五",
        language_code="en",
        is_premium=False,
        created_at=(datetime.now() - timedelta(days=2)).isoformat(),
        updated_at=datetime.now().isoformat()
    )
]

MOCK_ADMINS = [
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


# API路由
@app.get("/")
async def root():
    """根路径健康检查"""
    return {"message": "Telegram Bot Admin API", "status": "running"}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """获取仪表板统计数据"""
    total_users = len(MOCK_USERS)
    active_users = len([u for u in MOCK_USERS if u.updated_at])
    new_users_today = 1  # 模拟今日新用户
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "new_users_today": new_users_today,
        "total_messages": total_users * 12,
        "messages_today": new_users_today * 3,
        "bot_uptime": "运行中",
        "last_updated": datetime.now().isoformat(),
        "trends": {
            "users_growth": 12.5,
            "messages_growth": 8.3,
            "activity_growth": 5.2
        },
        "recent_activity": [
            {
                "id": 1,
                "type": "user_joined",
                "message": "新用户注册",
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "user": f"用户{total_users}"
            },
            {
                "id": 2,
                "type": "message_sent", 
                "message": "发送消息",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "user": f"用户{total_users-1 if total_users > 0 else 0}"
            },
            {
                "id": 3,
                "type": "bot_command",
                "message": "执行命令 /start",
                "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "user": f"用户{total_users-2 if total_users > 1 else 0}"
            }
        ]
    }


@app.get("/api/users", response_model=UsersListResponse)
async def get_users_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词")
):
    """获取用户列表"""
    users = MOCK_USERS.copy()
    
    # 搜索过滤
    if search:
        users = [
            u for u in users 
            if (search.lower() in (u.username or "").lower() or
                search.lower() in (u.first_name or "").lower() or
                search.lower() in (u.last_name or "").lower())
        ]
    
    total = len(users)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_users = users[start_idx:end_idx]
    
    return UsersListResponse(
        items=paginated_users,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user_detail(user_id: int):
    """获取用户详情"""
    user = next((u for u in MOCK_USERS if u.id == user_id), None)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@app.get("/api/admins", response_model=AdminsListResponse)
async def get_admins_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取管理员列表"""
    total = len(MOCK_ADMINS)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_admins = MOCK_ADMINS[start_idx:end_idx]
    
    return AdminsListResponse(
        items=paginated_admins,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@app.get("/api/admins/{admin_id}", response_model=AdminResponse)
async def get_admin_detail(admin_id: int):
    """获取管理员详情"""
    admin = next((a for a in MOCK_ADMINS if a.id == admin_id), None)
    if not admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="管理员不存在")
    return admin


if __name__ == "__main__":
    import uvicorn
    print("🚀 启动简化API服务...")
    print("📍 地址: http://localhost:8000")
    print("🔧 调试模式: 开启")
    print("=" * 50)
    
    uvicorn.run(app, host="localhost", port=8000, reload=True)