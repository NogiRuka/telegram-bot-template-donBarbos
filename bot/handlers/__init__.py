from aiogram import Router

from . import export_users, info, menu, start, support
from . import group_config, group_message_saver, message_export, admin_commands

# 导入测试模块（仅在开发模式下）
try:
    from bot.tests.router import test_router
    TESTS_AVAILABLE = True
except ImportError:
    TESTS_AVAILABLE = False


def get_handlers_router() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(info.router)
    router.include_router(support.router)
    router.include_router(menu.router)
    router.include_router(export_users.router)
    
    # 群组消息保存功能
    router.include_router(group_config.router)
    router.include_router(group_message_saver.router)
    router.include_router(message_export.router)
    router.include_router(admin_commands.router)
    
    # 在开发模式下添加测试路由
    if TESTS_AVAILABLE:
        from bot.core.config import settings
        if getattr(settings, 'DEBUG', False):
            router.include_router(test_router)

    return router
