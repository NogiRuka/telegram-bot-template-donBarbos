from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from aiogram.enums import ChatType
from bot.services.config_service import get_config
from bot.utils.message import delete_message_after_delay
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

        # 忽略服务消息 (入群/退群/置顶等)
        if is_message:
            msg: Message = event  # type: ignore
            if (
                msg.new_chat_members
                or msg.left_chat_member
                or msg.group_chat_created
                or msg.supergroup_chat_created
                or msg.channel_chat_created
                or msg.pinned_message
                or msg.migrate_to_chat_id
                or msg.migrate_from_chat_id
            ):
                # 服务消息直接放行，交给专门的 handler (如 member_events) 处理
                # 因为 member_events 中可能包含重要的审计日志或 Emby 清理逻辑
                # 即使机器人"功能"关闭，核心的管理功能（如踢人时的清理）通常不应受影响，或者由 handler 内部判断
                # 但这里的 BotEnabledMiddleware 主要是控制"用户交互"功能
                # 如果放行，member_events 会执行；如果不放行，member_events 不执行。
                # 假设 member_events 属于核心管理功能，不受全局开关限制（或者理应不受限制），则应放行。
                return await handler(event, data)

        user = event.from_user  # type: ignore[assignment]
        first = event  # Message | CallbackQuery
        if not user:
            return await handler(event, data)

        # 解析角色
        role = await _resolve_role(session, user.id)

        # 判断是否允许通过
        allow = True
        # 允许所有者和管理员在维护模式下使用
        if role not in ("owner", "admin") and session is not None:
            enabled_all = bool(await get_config(session, "bot.features.enabled") or False)
            allow = enabled_all

        if allow:
            return await handler(event, data)

        # 机器人关闭: 拦截并提示
        
        # 如果是服务消息（如成员变动），则静默拦截，不发送提示
        # (上面的逻辑已经放行了服务消息，这里是双重保险，或者处理漏网之鱼)
        if is_message:
            msg: Message = event  # type: ignore
            if (
                msg.new_chat_members
                or msg.left_chat_member
                or msg.group_chat_created
                or msg.supergroup_chat_created
                or msg.channel_chat_created
                or msg.pinned_message
                or msg.migrate_to_chat_id
                or msg.migrate_from_chat_id
            ):
                return await handler(event, data) # 放行

        try:
            if is_callback:
                await first.answer("🔴 机器人已关闭", show_alert=True)  # type: ignore[attr-defined]
            elif is_message:
                msg: Message = event  # type: ignore
                # 如果是群组，使用引用回复；如果是私聊，直接回复
                is_group = msg.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
                
                reply_msg = await msg.reply("🔴 机器人已关闭") if is_group else await msg.answer("🔴 机器人已关闭")
                delete_message_after_delay(reply_msg, 3)
        except TelegramAPIError:
            pass
        return None
