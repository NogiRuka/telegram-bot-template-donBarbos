from aiogram import Router

from .admin.ban import router as ban_router
from .admin.disable_user import router as disable_user_router
from .admin.enable_user import router as enable_user_router
from .admin.group import router as admin_group_router
from .admin.save_emby import router as save_emby_router
from .admin.stats import router as admin_stats_router
from .admin.submission_review import router as submission_review_router
from .admin.unban import router as unban_router
from .owner import get_owner_command_router
from .user.files import router as user_files_router
from .user.help import router as help_router
from .user.red_packet import router as user_red_packet_router
from bot.core.config import settings
from bot.handlers.command.test.dynamic_redpacket_preview import router as test_dynamic_redpacket_preview_router


def get_command_router() -> Router:
    """
    聚合通用命令路由
    """
    router = Router(name="command")
    # 管理员命令
    router.include_router(ban_router)
    router.include_router(disable_user_router)
    router.include_router(enable_user_router)
    router.include_router(unban_router)
    router.include_router(save_emby_router)
    router.include_router(submission_review_router)
    router.include_router(admin_group_router)
    router.include_router(admin_stats_router)
    router.include_router(user_files_router)
    router.include_router(user_red_packet_router)
    # 帮助命令
    router.include_router(help_router)
    # 所有者命令
    router.include_router(get_owner_command_router())
    # 测试命令仅在开发模式下启用
    if getattr(settings, "DEBUG", False):
        router.include_router(test_dynamic_redpacket_preview_router)
    return router
