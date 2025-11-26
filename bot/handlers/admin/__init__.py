from aiogram import Router

from .admin_commands import router as admin_commands_router
from .panel import router as admin_panel_router


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
    router.include_router(admin_panel_router)
    return router
