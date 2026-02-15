from aiogram import Router

from .features import router as owner_features_router
from .commands import router as owner_commands_router


def get_owner_command_router() -> Router:
    router = Router(name="owner_command")
    router.include_router(owner_features_router)
    router.include_router(owner_commands_router)
    return router
