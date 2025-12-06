from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware

from bot.core.loader import bot
from bot.services.main_message import MainMessageService

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject

# 模块级单例，确保所有请求共享同一个实例
_main_message_service: MainMessageService | None = None


def get_main_message_service() -> MainMessageService:
    """获取 MainMessageService 单例

    功能说明:
    - 返回全局唯一的 MainMessageService 实例

    输入参数:
    - 无

    返回值:
    - MainMessageService: 单例服务实例
    """
    global _main_message_service
    if _main_message_service is None:
        _main_message_service = MainMessageService(bot)
    return _main_message_service


class MainMessageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """主消息服务注入中间件

        功能说明:
        - 在处理器调用前注入 `main_msg: MainMessageService` 到数据字典
        - 提供统一的主消息管理服务, 便于在各处理器中直接使用

        输入参数:
        - handler: 下游处理器函数
        - event: Telegram 更新事件对象
        - data: 处理器上下文数据字典

        返回值:
        - Any: 下游处理器返回值
        """
        data["main_msg"] = get_main_message_service()
        return await handler(event, data)
