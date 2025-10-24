"""
测试模块路由注册

将测试相关的handler注册到主路由中
"""
from aiogram import Router

from bot.tests.chat_info_handler import router as chat_info_router

# 创建测试模块的主路由
test_router = Router()

# 注册所有测试相关的子路由
test_router.include_router(chat_info_router)

# 导出主路由
__all__ = ["test_router"]