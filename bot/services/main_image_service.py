from __future__ import annotations
from datetime import datetime
from typing import Any

import random
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import DISPLAY_MODE_SFW, DISPLAY_MODE_NSFW, DISPLAY_MODE_RANDOM
from bot.database.models import (
    MainImageModel,
    MainImageScheduleModel,
    UserExtendModel,
)
from bot.services.config_service import get_config
from bot.utils.datetime import now
from bot.config.constants import KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED


class MainImageService:
    @staticmethod
    async def get_user_prefs(session: AsyncSession, user_id: int) -> dict[str, Any]:
        """获取用户主图偏好
        
        功能说明:
        - 从 user_extend 读取展示模式与 NSFW 解锁状态
        
        输入参数:
        - session: 异步数据库会话
        - user_id: 用户ID
        
        返回值:
        - dict[str, Any]: {display_mode, nsfw_unlocked, last_image_id}
        """
        result = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user_id))
        ext = result.scalar_one_or_none()
        if not ext:
            return {"display_mode": DISPLAY_MODE_SFW, "nsfw_unlocked": False, "last_image_id": None}
        return {
            "display_mode": ext.display_mode or DISPLAY_MODE_SFW,
            "nsfw_unlocked": bool(ext.nsfw_unlocked),
            "last_image_id": ext.last_image_id,
        }

    @staticmethod
    async def record_display(session: AsyncSession, user_id: int, image_id: int) -> None:
        """记录主图展示历史
        
        功能说明:
        - 更新用户的 last_image_id
        - 记录展示时间到 extra_data (可选)
        
        输入参数:
        - session: 异步数据库会话
        - user_id: 用户ID
        - image_id: 展示的主图ID
        """
        stmt = select(UserExtendModel).where(UserExtendModel.user_id == user_id)
        result = await session.execute(stmt)
        ext = result.scalar_one_or_none()
        if ext:
            ext.last_image_id = image_id
            
            # 更新 extra_data (保留原有数据)
            data = dict(ext.extra_data) if ext.extra_data else {}
            data["last_display_at"] = now()
            ext.extra_data = data
            
            await session.commit()

    @staticmethod
    async def select_main_image(session: AsyncSession, user_id: int) -> MainImageModel | None:
        """选择主图条目
        
        功能说明:
        - 优先选择当前时间窗口内的节日主图（按 priority 最小）
        - 否则根据用户展示模式与全局 NSFW 开关，从 SFW/NSFW 池中随机选择首个可用条目
        - **支持去重**: 尽量避免连续展示同一张图片 (依赖 last_image_id)
        
        输入参数:
        - session: 异步数据库会话
        - user_id: 用户ID
        
        返回值:
        - MainImageModel | None: 选中的主图记录
        """
        current_time = now()
        prefs = await MainImageService.get_user_prefs(session, user_id)
        last_id = prefs.get("last_image_id")
        nsfw_enabled = bool(await get_config(session, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED) or False)

        # 1. 节日主图优先
        # 获取当前时间段内的所有有效投放（过滤软删除），按优先级排序
        # 必须联表查询 MainImageModel 以确保图片本身也是有效（未删除且已启用）
        sched_stmt = (
            select(MainImageScheduleModel, MainImageModel)
            .join(MainImageModel, MainImageScheduleModel.image_id == MainImageModel.id)
            .where(
                MainImageScheduleModel.start_time <= current_time, 
                MainImageScheduleModel.end_time >= current_time,
                MainImageScheduleModel.is_deleted.is_(False),
                MainImageModel.is_deleted.is_(False),
                MainImageModel.is_enabled.is_(True),
                MainImageModel.source_type != "document"
            )
            .order_by(MainImageScheduleModel.priority.asc())
        )
        sched_res = await session.execute(sched_stmt)
        schedules = sched_res.all()
        
        if schedules:
            # 获取最高优先级（数值最小）
            best_priority = schedules[0][0].priority
            # 筛选出最高优先级的投放（可能存在多个）
            candidates = [(s, i) for s, i in schedules if s.priority == best_priority]
            
            # 过滤不符合 NSFW 约束的图片
            valid_candidates = []
            for s, img in candidates:
                if img.is_nsfw and not (nsfw_enabled and prefs["nsfw_unlocked"] and prefs["display_mode"] in (DISPLAY_MODE_NSFW, DISPLAY_MODE_RANDOM)):
                    continue
                valid_candidates.append(img)
            
            if valid_candidates:
                # 尝试去重
                filtered = [img for img in valid_candidates if img.id != last_id]
                if filtered:
                    return random.choice(filtered)
                return random.choice(valid_candidates)

        # 2. 根据用户模式选择池
        mode = prefs["display_mode"]
        allow_nsfw = nsfw_enabled and prefs["nsfw_unlocked"] and mode in (DISPLAY_MODE_NSFW, DISPLAY_MODE_RANDOM)

        # 优先选择符合模式的图片
        cond_stmt = select(MainImageModel).where(
            MainImageModel.is_enabled.is_(True),
            MainImageModel.is_deleted.is_(False),
            MainImageModel.source_type != "document"
        )
        if mode == DISPLAY_MODE_SFW:
            cond_stmt = cond_stmt.where(MainImageModel.is_nsfw.is_(False))
        elif mode == DISPLAY_MODE_NSFW:
            if allow_nsfw:
                cond_stmt = cond_stmt.where(MainImageModel.is_nsfw.is_(True))
            else:
                # 即使选了NSFW但没权限/未开启，回退到SFW
                cond_stmt = cond_stmt.where(MainImageModel.is_nsfw.is_(False))
        elif mode == DISPLAY_MODE_RANDOM:
            if not allow_nsfw:
                cond_stmt = cond_stmt.where(MainImageModel.is_nsfw.is_(False))
        
        # 尝试去重逻辑
        final_stmt = cond_stmt
        if last_id is not None:
            final_stmt = final_stmt.where(MainImageModel.id != last_id)
        
        # 随机选择
        final_stmt = final_stmt.order_by(func.random()).limit(1)
        cond_res = await session.execute(final_stmt)
        result = cond_res.scalar_one_or_none()
        
        if result:
            return result
            
        # 如果去重后没结果（可能只有一张图），则允许重复
        if last_id is not None:
            fallback_stmt = cond_stmt.order_by(func.random()).limit(1)
            fallback_res = await session.execute(fallback_stmt)
            return fallback_res.scalar_one_or_none()
            
        return None
