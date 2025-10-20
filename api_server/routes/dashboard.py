"""
仪表板API路由
提供仪表板统计数据接口
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from bot.database.database import sessionmaker
from bot.database.models import UserModel

router = APIRouter()


async def get_user_stats() -> Dict[str, Any]:
    """
    获取用户统计数据
    
    Returns:
        Dict[str, Any]: 用户统计信息
    """
    try:
        async with sessionmaker() as session:
            from sqlalchemy import func, select
            
            # 总用户数
            total_users_result = await session.execute(
                select(func.count(UserModel.user_id))
            )
            total_users = total_users_result.scalar() or 0
            
            # 今日新用户（最近24小时）
            today = datetime.now() - timedelta(days=1)
            new_users_today_result = await session.execute(
                select(func.count(UserModel.user_id))
                .where(UserModel.created_at >= today)
            )
            new_users_today = new_users_today_result.scalar() or 0
            
            # 活跃用户（最近7天有活动）
            week_ago = datetime.now() - timedelta(days=7)
            active_users_result = await session.execute(
                select(func.count(UserModel.user_id))
                .where(UserModel.updated_at >= week_ago)
            )
            active_users = active_users_result.scalar() or 0
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "new_users_today": new_users_today
            }
            
    except Exception as e:
        logger.error(f"获取用户统计数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户统计数据失败")


@router.get("/dashboard/stats")
async def get_dashboard_stats(user_stats: Dict[str, Any] = Depends(get_user_stats)):
    """
    获取仪表板统计数据
    
    Returns:
        Dict[str, Any]: 仪表板统计信息
    """
    try:
        # 基础统计数据
        total_users = user_stats["total_users"]
        active_users = user_stats["active_users"]
        new_users_today = user_stats["new_users_today"]
        
        # 模拟其他统计数据
        stats = {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_today": new_users_today,
            "total_messages": total_users * 12,  # 估算消息数
            "messages_today": new_users_today * 3,  # 估算今日消息
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
        
        return stats
        
    except Exception as e:
        logger.error(f"获取仪表板统计数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取仪表板统计数据失败")