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
                # 服务消息直接放行（交给后续 handler 处理，例如 member_events）
                # 或者直接拦截但不提示？
                # 通常建议放行，让 member_events 决定是否处理，或者在这里拦截但不回复。
                # 鉴于"机器人已关闭"通常是指"不响应命令/对话"，服务消息记录可能仍需进行。
                # 但如果完全禁用，也可以拦截。
                # 根据用户反馈 "会向群组里发送机器人已关闭的消息"，说明这里需要拦截但不提示，或者放行。
                # 如果放行，后续 handler 可能会处理入群欢迎等，这取决于是否希望在禁用期间仍有欢迎语。
                # 如果希望彻底静默，则拦截并 return None，且不发送提示。
                
                # 这里选择：服务消息不触发 "机器人已关闭" 的回复，但允许通过（以便记录日志或特定处理），
                # 或者拦截但不回复。
                # 考虑到用户意图是 "不要发送已关闭消息"，最安全的做法是：如果是服务消息，且机器人关闭，则静默拦截或放行。
                # 如果放行，member_events 可能会响应。如果机器人是全局关闭，理应不响应欢迎语。
                # 所以逻辑应为：检查是否关闭 -> 关闭 -> 检查是否服务消息 -> 是 -> 静默拦截 (return None)；否 -> 提示并拦截。
                pass

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
        
        # 如果是服务消息（如成员变动），则静默拦截，不发送提示
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
                return None

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
