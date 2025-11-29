from aiogram import Router

from .account import router as account_router


def get_user_router() -> Router:
    """聚合用户相关路由

    功能说明:
    - 汇总用户账号中心等路由为一个 Router

    输入参数:
    - 无

    返回值:
    - Router: 用户聚合路由
    """
    router = Router(name="user")
    router.include_router(account_router)
    return router
