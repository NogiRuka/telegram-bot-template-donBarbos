from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from bot.services.config_service import get_config
from bot.utils.permissions import _resolve_role

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject
    from sqlalchemy.ext.asyncio import AsyncSession


class BotEnabledMiddleware(BaseMiddleware):
    """机器人全局开关中间件

    功能说明:
    - 当配置 `bot.features.enabled` 关闭时, 拦截所有非所有者的操作
    - 对于所有者不受影响, 其操作始终允许
    - 支持消息与按钮回调两类事件

    输入参数:
    - 无

    返回值:
    - BaseMiddleware: 中间件实例
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """拦截处理入口

        功能说明:
        - 读取会话与用户, 判断是否为所有者
        - 当机器人关闭时, 非所有者的消息与回调直接提示不可用并阻止后续处理

        输入参数:
        - handler: 下一个处理函数
        - event: Aiogram 事件对象 (Message/CallbackQuery/Update)
        - data: 上下文字典 (包含 session / bot 等)

        返回值:
        - Any: 当允许时返回下游处理结果; 当拦截时返回 None
        """
        session: AsyncSession | None = data.get("session")  # 由 DatabaseMiddleware 注入

        # 仅处理 Message 与 CallbackQuery
        is_message = isinstance(event, Message)
        is_callback = isinstance(event, CallbackQuery)
        if not (is_message or is_callback):
            return await handler(event, data)

        user = event.from_user  # type: ignore[assignment]
        first = event  # Message | CallbackQuery
        if not user:
            return await handler(event, data)

        # 解析角色
        role = await _resolve_role(session, user.id)

        # 判断是否允许通过
        allow = True
        if role != "owner" and session is not None:
            enabled_all = bool(await get_config(session, "bot.features.enabled") or False)
            allow = enabled_all

        if allow:
            return await handler(event, data)

        # 机器人关闭: 拦截并提示
        try:
            if is_callback:
                await first.answer("❌ 机器人已关闭, 仅所有者可操作", show_alert=True)  # type: ignore[attr-defined]
            elif is_message:
                await first.answer("❌ 机器人已关闭, 仅所有者可操作")  # type: ignore[attr-defined]
        except TelegramAPIError:
            pass
        return None
