from aiogram import Router

from .account import router as account_router
from .avatar import router as avatar_router
from .checkin import router as checkin_router
from .devices import router as devices_router
from .info import router as info_router
from .lines import router as lines_router
from .password import router as password_router
from .private_message_saver import router as private_message_saver_router
from .profile import router as profile_router
from .quiz_handler import router as quiz_router
from .quiz_submit import router as quiz_submit_router
from .red_packet import router as red_packet_router
from .register import router as register_router
from .store import router as store_router
from .submission import router as submission_router
from .submission_my import router as submission_my_router
from .submission_request import router as submission_request_router
from .submission_submit import router as submission_submit_router
from .tags import router as tags_router


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
    router.include_router(store_router)
    router.include_router(avatar_router)
    router.include_router(quiz_router)
    router.include_router(quiz_submit_router)
    router.include_router(submission_router)
    router.include_router(submission_request_router)
    router.include_router(submission_submit_router)
    router.include_router(submission_my_router)
    router.include_router(red_packet_router)
    # private_message_saver_router 应该放在最后，以免拦截其他处理器的消息
    router.include_router(private_message_saver_router)
    return router
