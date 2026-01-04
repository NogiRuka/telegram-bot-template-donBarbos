from aiogram import Dispatcher
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

from .album import AlbumMiddleware
from .auth import AuthMiddleware
from .bot_enabled import BotEnabledMiddleware
from .database import DatabaseMiddleware
from .logging import LoggingMiddleware
from .main_message import MainMessageMiddleware
from .quiz_trigger import QuizTriggerMiddleware
from .throttling import ThrottlingMiddleware


def register_middlewares(dp: Dispatcher) -> None:
    # 1. 首先注册相册中间件 (外层)，把多条消息合并成一条
    dp.message.outer_middleware(AlbumMiddleware())
    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(MainMessageMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware())

    dp.message.middleware(BotEnabledMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(QuizTriggerMiddleware())

    dp.callback_query.middleware(BotEnabledMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.callback_query.middleware(QuizTriggerMiddleware())
    dp.callback_query.middleware(CallbackAnswerMiddleware())
