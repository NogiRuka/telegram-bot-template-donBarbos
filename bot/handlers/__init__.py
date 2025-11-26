from aiogram import Router

from . import export_users, info, menu, start, support
from .admin import get_admin_router
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
    router.include_router(info.router)
    router.include_router(support.router)
    router.include_router(menu.router)
    router.include_router(export_users.router)

    # 群组与管理员聚合路由
    router.include_router(get_group_router())
    router.include_router(get_admin_router())
    router.include_router(get_user_router())
    router.include_router(get_owner_router())

    # 在开发模式下添加测试路由
    if TESTS_AVAILABLE and getattr(settings, "DEBUG", False):
        router.include_router(test_router)

    return router
