from aiogram import Dispatcher
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

from .auth import AuthMiddleware
from .database import DatabaseMiddleware
from .logging import LoggingMiddleware
from .throttling import ThrottlingMiddleware


def register_middlewares(dp: Dispatcher) -> None:
    dp.message.outer_middleware(ThrottlingMiddleware())

    dp.update.outer_middleware(LoggingMiddleware())

    dp.update.outer_middleware(DatabaseMiddleware())

    dp.message.middleware(AuthMiddleware())

    dp.callback_query.middleware(CallbackAnswerMiddleware())
