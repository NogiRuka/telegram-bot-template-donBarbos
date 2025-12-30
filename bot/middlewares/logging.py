from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import CancelHandler
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models.audit_log import AuditLogModel, ActionType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import (
        CallbackQuery,
        ChatMemberUpdated,
        InlineQuery,
        Message,
        PreCheckoutQuery,
        TelegramObject,
    )


class LoggingMiddleware(BaseMiddleware):
    """
    全中文日志记录中间件
    
    功能:
    1. 记录所有 Update 事件的日志到控制台
    2. 将 /start 和 /gf 等关键命令记录到数据库审计表
    """

    def __init__(self) -> None:
        self.logger = logger
        super().__init__()

    async def _record_command_audit(self, message: Message, session: AsyncSession) -> None:
        """记录命令审计日志"""
        if not message.text or not message.text.startswith("/"):
            return

        command = message.text.split()[0].lower()
        if command not in ["/start", "/gf", "/get_file"]:
            return

        try:
            audit = AuditLogModel(
                operator_id=message.from_user.id if message.from_user else None,
                operator_name=message.from_user.full_name if message.from_user else None,
                user_id=message.from_user.id if message.from_user else None,
                action_type=ActionType.USER_LOGIN if command == "/start" else ActionType.ADMIN_QUERY,
                target_type="file" if command in ["/gf", "/get_file"] else "system",
                target_id=command,
                description=f"用户执行命令: {message.text}",
                details={
                    "chat_id": message.chat.id,
                    "chat_type": message.chat.type,
                    "message_id": message.message_id,
                    "raw_text": message.text
                },
                ip_address=None,  # Telegram API 不提供用户 IP
                user_agent="Telegram Bot"
            )
            session.add(audit)
            await session.commit()
        except Exception as e:
            self.logger.error(f"记录审计日志失败: {e}")

    def process_message(self, message: Message) -> dict[str, Any]:
        """处理消息"""
        # 将 Key 修改为中文
        print_attrs: dict[str, Any] = {"聊天类型": message.chat.type}

        if message.from_user:
            print_attrs["用户ID"] = message.from_user.id

        if message.text:
            print_attrs["文本内容"] = message.text

        if message.video:
            print_attrs["视频附言"] = message.caption
            print_attrs["附言实体"] = message.caption_entities
            print_attrs["视频ID"] = message.video.file_id
            print_attrs["视频唯一ID"] = message.video.file_unique_id

        if message.audio:
            print_attrs["音频时长"] = message.audio.duration
            print_attrs["文件大小"] = message.audio.file_size

        if message.photo:
            print_attrs["图片附言"] = message.caption
            print_attrs["附言实体"] = message.caption_entities
            # 取最后一张（最高清）
            print_attrs["图片ID"] = message.photo[-1].file_id
            print_attrs["图片唯一ID"] = message.photo[-1].file_unique_id

        return print_attrs

    def process_callback_query(self, callback_query: CallbackQuery) -> dict[str, Any]:
        """处理按钮回调"""
        print_attrs: dict[str, Any] = {
            "查询ID": callback_query.id,
            "回调数据": callback_query.data,
            "用户ID": callback_query.from_user.id,
            "内联消息ID": callback_query.inline_message_id,
        }

        if callback_query.message:
            print_attrs["消息ID"] = callback_query.message.message_id
            print_attrs["聊天类型"] = callback_query.message.chat.type
            print_attrs["聊天ID"] = callback_query.message.chat.id

        return print_attrs

    def process_inline_query(self, inline_query: InlineQuery) -> dict[str, Any]:
        """处理内联搜索"""
        return {
            "查询ID": inline_query.id,
            "用户ID": inline_query.from_user.id,
            "搜索内容": inline_query.query,
            "偏移量": inline_query.offset,
            "聊天类型": inline_query.chat_type,
            "位置信息": inline_query.location,
        }

    def process_pre_checkout_query(self, pre_checkout_query: PreCheckoutQuery) -> dict[str, Any]:
        """处理支付预检"""
        return {
            "查询ID": pre_checkout_query.id,
            "用户ID": pre_checkout_query.from_user.id,
            "货币类型": pre_checkout_query.currency,
            "总金额": pre_checkout_query.total_amount,
            "发票负载": pre_checkout_query.invoice_payload,
            "物流选项": pre_checkout_query.shipping_option_id,
        }

    def process_my_chat_member(self, my_chat_member: ChatMemberUpdated) -> dict[str, Any]:
        """处理机器人自身状态"""
        return {
            "用户ID": my_chat_member.from_user.id,
            "聊天ID": my_chat_member.chat.id,
            "新状态": my_chat_member.new_chat_member.status,
        }

    def process_chat_member(self, chat_member: ChatMemberUpdated) -> dict[str, Any]:
        """处理成员变动"""
        return {
            "用户ID": chat_member.from_user.id,
            "聊天ID": chat_member.chat.id,
            "旧状态": chat_member.old_chat_member.status,
            "新状态": chat_member.new_chat_member.status,
        }

    def _log_event(self, event_name: str, attributes: dict[str, Any]) -> None:
        """统一日志打印格式"""
        # 过滤 None 值，并将 key 和 value 拼接到一起
        log_parts = [f"{key}: {value}" for key, value in attributes.items() if value is not None]
        logger_msg = f"{event_name} | " + " | ".join(log_parts)
        self.logger.info(logger_msg)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # 定义：(属性名, 日志前缀, 处理函数)
        event_handlers = [
            ("message", "收到消息", self.process_message),
            ("callback_query", "收到按钮回调", self.process_callback_query),
            ("inline_query", "收到内联搜索", self.process_inline_query),
            ("pre_checkout_query", "收到支付预检", self.process_pre_checkout_query),
            ("my_chat_member", "机器人状态变更", self.process_my_chat_member),
            ("chat_member", "群成员状态变更", self.process_chat_member),
        ]

        # 1. 优先检查 Update 对象中的属性
        for attr_name, log_prefix, process_func in event_handlers:
            target_obj = getattr(event, attr_name, None)
            if target_obj:
                self._log_event(log_prefix, process_func(target_obj))
                
                # 记录特定命令的审计日志
                if attr_name == "message" and "session" in data:
                    await self._record_command_audit(target_obj, data["session"])
                break
        else:
            # 2. 备用检查：如果 event 本身就是 Message/CallbackQuery 等对象（非 Update 包裹）
            # 为了避免 import 循环或过多依赖，这里做简单的类名字符串匹配，或者你可以显式 import
            event_type = type(event).__name__

            if event_type == "Message":
                self._log_event("收到消息", self.process_message(event))  # type: ignore
                if "session" in data:
                    await self._record_command_audit(event, data["session"])  # type: ignore
            elif event_type == "CallbackQuery":
                self._log_event("收到按钮回调", self.process_callback_query(event))  # type: ignore
            elif event_type == "InlineQuery":
                self._log_event("收到内联搜索", self.process_inline_query(event))  # type: ignore
            # ... 其他类型如有需要可继续添加

        return await handler(event, data)
