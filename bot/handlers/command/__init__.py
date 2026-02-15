from aiogram import Router

from .admin.ban import router as ban_router
from .admin.group import router as admin_group_router
from .admin.save_emby import router as save_emby_router
from .admin.stats import router as admin_stats_router
from .admin.submission_review import router as submission_review_router
from .admin.unban import router as unban_router
from .common.help import router as help_router
from .user.files import router as user_files_router


def get_command_router() -> Router:
    """
    聚合通用命令路由
    """
    router = Router(name="command")
    # 管理员命令
    router.include_router(ban_router)
    router.include_router(unban_router)
    router.include_router(save_emby_router)
    router.include_router(submission_review_router)
    router.include_router(admin_group_router)
    router.include_router(admin_stats_router)
    # 用户命令
    router.include_router(user_files_router)
    # 帮助命令
    router.include_router(help_router)
    return router
