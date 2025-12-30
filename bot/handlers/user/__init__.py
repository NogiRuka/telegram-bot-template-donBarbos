from aiogram import Router

from .account import router as account_router
from .avatar import router as avatar_router
from .checkin import router as checkin_router
from .commands import router as commands_router
from .devices import router as devices_router
from .files import router as files_router
from .info import router as info_router
from .lines import router as lines_router
from .password import router as password_router
from .profile import router as profile_router
from .register import router as register_router
from .store import router as store_router
from .tags import router as tags_router
from .private_message_saver import router as private_message_saver_router


def get_user_router() -> Router:
    """聚合用户相关路由

    功能说明:
    - 汇总用户账号中心/注册/信息/设备/线路/密码/个人信息等路由为一个 Router

    输入参数:
    - 无

    返回值:
    - Router: 用户聚合路由
    """
    router = Router(name="user")
    router.include_router(account_router)
    router.include_router(register_router)
    router.include_router(info_router)
    router.include_router(lines_router)
    router.include_router(devices_router)
    router.include_router(password_router)
    router.include_router(profile_router)
    router.include_router(tags_router)
    router.include_router(checkin_router)
    router.include_router(commands_router)
    router.include_router(store_router)
    router.include_router(avatar_router)
    router.include_router(files_router)
    router.include_router(private_message_saver_router)
    return router
