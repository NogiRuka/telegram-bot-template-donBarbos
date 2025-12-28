from aiogram import Router

from .admin_commands import router as admin_commands_router
from .copywriting import router as admin_copywriting_router
from .groups import router as admin_groups_router
from .hitokoto import router as admin_hitokoto_router
from .home import router as admin_home_router
from .notification import router as admin_notification_router
from .registration import router as admin_registration_router
from .stats import router as admin_stats_router
from .store_admin import router as admin_store_router
from .currency_admin import router as admin_currency_router


def get_admin_router() -> Router:
    """
    聚合管理员相关路由

    功能说明:
    - 汇总管理员命令等路由为一个 Router

    输入参数:
    - 无

    返回值:
    - Router: 管理员聚合路由
    """
    router = Router(name="admin")
    router.include_router(admin_commands_router)
    router.include_router(admin_home_router)
    router.include_router(admin_groups_router)
    router.include_router(admin_stats_router)
    router.include_router(admin_registration_router)
    router.include_router(admin_hitokoto_router)
    router.include_router(admin_copywriting_router)
    router.include_router(admin_notification_router)
    router.include_router(admin_store_router)
    router.include_router(admin_currency_router)
    return router
