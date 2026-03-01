from aiogram import Router

from .admin import get_admin_command_router
from .owner import get_owner_command_router
from .user import get_user_command_router
from bot.core.config import settings
from bot.handlers.command.test.dynamic_redpacket_preview import router as test_dynamic_redpacket_preview_router


def get_command_router() -> Router:
    """
    聚合通用命令路由
    """
    router = Router(name="command")
    
    # 管理员命令 (动态加载)
    router.include_router(get_admin_command_router())
    
    # 用户命令 (动态加载)
    router.include_router(get_user_command_router())
    
    # 所有者命令 (动态加载)
    router.include_router(get_owner_command_router())
    
    # 测试命令仅在开发模式下启用
    if getattr(settings, "DEBUG", False):
        router.include_router(test_dynamic_redpacket_preview_router)
    return router
