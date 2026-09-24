from aiogram import Router

from .admins import router as owner_admins_router
from .commands import router as owner_commands_router
from .features import router as owner_features_router


def get_owner_command_router() -> Router:
    router = Router(name="owner_command")
    router.include_router(owner_admins_router)
    router.include_router(owner_features_router)
    router.include_router(owner_commands_router)
    return router
