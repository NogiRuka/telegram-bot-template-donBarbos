from aiogram import Dispatcher
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

from .auth import AuthMiddleware
from .bot_enabled import BotEnabledMiddleware
from .database import DatabaseMiddleware
from .logging import LoggingMiddleware
from .throttling import ThrottlingMiddleware


def register_middlewares(dp: Dispatcher) -> None:
    dp.message.outer_middleware(ThrottlingMiddleware())

    dp.update.outer_middleware(LoggingMiddleware())

    dp.update.outer_middleware(DatabaseMiddleware())

    dp.message.middleware(BotEnabledMiddleware())
    dp.message.middleware(AuthMiddleware())

    dp.callback_query.middleware(BotEnabledMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.callback_query.middleware(CallbackAnswerMiddleware())
