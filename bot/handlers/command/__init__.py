from aiogram import Router

from .ban import router as ban_router
from .save_emby import router as save_emby_router
from .submission_review import router as submission_review_router
from .unban import router as unban_router


def get_command_router() -> Router:
    """
    聚合通用命令路由
    """
    router = Router(name="command")
    router.include_router(ban_router)
    router.include_router(unban_router)
    router.include_router(save_emby_router)
    router.include_router(submission_review_router)
    return router
