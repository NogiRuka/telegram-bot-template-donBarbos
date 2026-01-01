from aiogram import Router

from . import start
from .admin import get_admin_router
from .command import get_command_router
from .group import get_group_router
from .owner import get_owner_router
from .user import get_user_router
from bot.core.config import settings

# 导入测试模块(仅在开发模式下)
try:
    from bot.tests.router import test_router

    TESTS_AVAILABLE = True
except ImportError:
    TESTS_AVAILABLE = False


def get_handlers_router() -> Router:
    router = Router()
    router.include_router(start.router)

    # 注册功能路由 (优先级: 管理员 > 用户 > 所有者 > 群组)
    # 注意: 群组路由包含消息保存的通配符处理器，必须放在最后
    router.include_router(get_admin_router())
    router.include_router(get_command_router())
    router.include_router(get_user_router())
    router.include_router(get_owner_router())
    router.include_router(get_group_router())

    # 在开发模式下添加测试路由
    if TESTS_AVAILABLE and getattr(settings, "DEBUG", False):
        router.include_router(test_router)

    return router
