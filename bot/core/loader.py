from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from bot.core.config import settings

app = web.Application()

token = settings.BOT_TOKEN

bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# 使用内存存储替代Redis存储，适用于开发和测试环境
storage = MemoryStorage()

dp = Dispatcher(storage=storage)

DEBUG = settings.DEBUG
