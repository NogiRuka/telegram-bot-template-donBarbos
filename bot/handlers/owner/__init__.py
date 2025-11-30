from aiogram import Router

from .admin_perms import router as owner_admin_perms_router
from .admins import router as owner_admins_router
from .features import router as owner_features_router
from .home import router as owner_home_router


def get_owner_router() -> Router:
    """聚合所有者相关路由

    功能说明:
    - 汇总所有者主面板、功能面板与管理员面板

    输入参数:
    - 无

    返回值:
    - Router: 所有者聚合路由
    """
    router = Router(name="owner")
    router.include_router(owner_home_router)
    router.include_router(owner_features_router)
    router.include_router(owner_admins_router)
    router.include_router(owner_admin_perms_router)
    return router
