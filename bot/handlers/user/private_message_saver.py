"""
私聊消息保存处理器模块

本模块实现了自动保存私聊消息的功能，
自动保存所有私聊消息到数据库。
"""

import json
import logging
from typing import Any

from aiogram import F, Router, types
from aiogram.enums import ChatType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import MessageModel, MessageType

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = Router()

class PrivateMessageSaver:
    """
    私聊消息保存器类

    负责处理私聊消息的自动保存功能。
    """

    def __init__(self) -> None:
        pass

    def get_message_type(self, message: types.Message) -> MessageType:
        if message.photo:
            return MessageType.PHOTO
        if message.video:
            return MessageType.VIDEO
        if message.audio:
            return MessageType.AUDIO
        if message.voice:
            return MessageType.VOICE
        if message.document:
            return MessageType.DOCUMENT
        if message.sticker:
            return MessageType.STICKER
        if message.animation:
            return MessageType.ANIMATION
        if message.location:
            return MessageType.LOCATION
        if message.contact:
            return MessageType.CONTACT
        if message.poll:
            return MessageType.POLL
        if message.dice:
            return MessageType.DICE
        if message.game:
            return MessageType.GAME
        if message.invoice:
            return MessageType.INVOICE
        if message.successful_payment:
            return MessageType.SUCCESSFUL_PAYMENT
        if message.video_note:
            return MessageType.VIDEO_NOTE
        if message.venue:
            return MessageType.VENUE
        if message.web_app_data:
            return MessageType.WEB_APP_DATA
        if message.text:
            return MessageType.TEXT
        return MessageType.OTHER

    def extract_file_info(self, message: types.Message) -> dict[str, Any]:
        file_info = {
            "file_id": None,
            "file_unique_id": None,
            "file_size": None,
            "file_name": None,
            "mime_type": None,
        }
        if message.photo:
            largest_photo = max(message.photo, key=lambda x: x.file_size or 0)
            file_info.update(
                {
                    "file_id": largest_photo.file_id,
                    "file_unique_id": largest_photo.file_unique_id,
                    "file_size": largest_photo.file_size,
                }
            )
        elif message.video:
            file_info.update(
                {
                    "file_id": message.video.file_id,
                    "file_unique_id": message.video.file_unique_id,
                    "file_size": message.video.file_size,
                    "file_name": message.video.file_name,
                    "mime_type": message.video.mime_type,
                }
            )
        elif message.audio:
            file_info.update(
                {
                    "file_id": message.audio.file_id,
                    "file_unique_id": message.audio.file_unique_id,
                    "file_size": message.audio.file_size,
                    "file_name": message.audio.file_name,
                    "mime_type": message.audio.mime_type,
                }
            )
        elif message.voice:
            file_info.update(
                {
                    "file_id": message.voice.file_id,
                    "file_unique_id": message.voice.file_unique_id,
                    "file_size": message.voice.file_size,
                    "mime_type": message.voice.mime_type,
                }
            )
        elif message.document:
            file_info.update(
                {
                    "file_id": message.document.file_id,
                    "file_unique_id": message.document.file_unique_id,
                    "file_size": message.document.file_size,
                    "file_name": message.document.file_name,
                    "mime_type": message.document.mime_type,
                }
            )
        elif message.sticker:
            file_info.update(
                {
                    "file_id": message.sticker.file_id,
                    "file_unique_id": message.sticker.file_unique_id,
                    "file_size": message.sticker.file_size,
                }
            )
        elif message.animation:
            file_info.update(
                {
                    "file_id": message.animation.file_id,
                    "file_unique_id": message.animation.file_unique_id,
                    "file_size": message.animation.file_size,
                    "file_name": message.animation.file_name,
                    "mime_type": message.animation.mime_type,
                }
            )
        elif message.video_note:
            file_info.update(
                {
                    "file_id": message.video_note.file_id,
                    "file_unique_id": message.video_note.file_unique_id,
                    "file_size": message.video_note.file_size,
                }
            )
        return file_info

    def extract_entities(self, entities: list | None) -> str | None:
        if not entities:
            return None
        try:
            entities_data = []
            for entity in entities:
                entity_dict = {
                    "type": entity.type,
                    "offset": entity.offset,
                    "length": entity.length,
                }
                if entity.type in {"url", "text_link"}:
                    entity_dict["url"] = entity.url if hasattr(entity, "url") else None
                elif entity.type == "text_mention":
                    if hasattr(entity, "user") and entity.user:
                        entity_dict["user"] = {
                            "id": entity.user.id,
                            "first_name": entity.user.first_name,
                            "last_name": entity.user.last_name,
                            "username": entity.user.username,
                        }
                elif (
                    entity.type
                    in [
                        "bold",
                        "italic",
                        "underline",
                        "strikethrough",
                        "spoiler",
                        "code",
                        "pre",
                    ]
                    and entity.type == "pre"
                    and hasattr(entity, "language")
                ):
                    entity_dict["language"] = entity.language
                entities_data.append(entity_dict)
            return json.dumps(entities_data, ensure_ascii=False) if entities_data else None
        except Exception as e:
            logger.exception(f"❌ 提取实体信息失败: {e}")
            return None

    async def save_message(self, message: types.Message, session: AsyncSession) -> bool:
        try:
            message_type = self.get_message_type(message)
            is_forwarded = message.forward_from is not None or message.forward_from_chat is not None
            is_reply = message.reply_to_message is not None
            
            text_content = message.text or message.caption or ""
            
            file_info = self.extract_file_info(message)
            entities_json = self.extract_entities(message.entities) if message.entities else None
            caption_entities_json = (
                self.extract_entities(message.caption_entities) if message.caption_entities else None
            )
            
            message_record = MessageModel.create_from_telegram(
                message_id=message.message_id,
                user_id=message.from_user.id if message.from_user else 0,
                chat_id=message.chat.id,
                message_type=message_type,
                text_content=text_content[:1000] if text_content else None,
                caption=message.caption[:1000] if message.caption else None,
                entities=entities_json,
                caption_entities=caption_entities_json,
                file_id=file_info["file_id"],
                file_unique_id=file_info["file_unique_id"],
                file_size=file_info["file_size"],
                file_name=file_info["file_name"],
                mime_type=file_info["mime_type"],
                is_forwarded=is_forwarded,
                is_reply=is_reply,
            )

            if is_forwarded:
                if message.forward_from:
                    message_record.forward_from_user_id = message.forward_from.id
                elif message.forward_from_chat:
                    message_record.forward_from_chat_id = message.forward_from_chat.id
                if hasattr(message, "forward_from_message_id"):
                    message_record.forward_from_message_id = message.forward_from_message_id
            
            if is_reply and message.reply_to_message:
                message_record.reply_to_message_id = message.reply_to_message.message_id
                if message.reply_to_message.from_user:
                    message_record.reply_to_user_id = message.reply_to_message.from_user.id

            session.add(message_record)
            await session.commit()
            logger.debug(
                f"✅ 成功保存私聊消息: 用户={message.chat.id}, 消息ID={message.message_id}, 类型={message_type.value}"
            )
            return True
        except Exception as e:
            logger.exception(f"❌ 保存私聊消息失败: {e}")
            await session.rollback()
            return False

message_saver = PrivateMessageSaver()

@router.message(F.chat.type == ChatType.PRIVATE)
async def handle_private_message(message: types.Message, session: AsyncSession) -> None:
    """
    处理私聊消息

    自动保存私聊消息。

    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    await message_saver.save_message(message, session)

@router.edited_message(F.chat.type == ChatType.PRIVATE)
async def handle_edited_private_message(message: types.Message, session: AsyncSession) -> None:
    """
    处理私聊编辑消息
    """
    try:
        # 查找原始消息记录
        result = await session.execute(
            select(MessageModel).where(
                MessageModel.message_id == message.message_id,
                MessageModel.chat_id == message.chat.id,
                not MessageModel.is_deleted,
            )
        )

        existing_message = result.scalar_one_or_none()

        if existing_message:
            # 更新消息内容
            existing_message.text_content = (message.text or message.caption or "")[:1000]
            existing_message.caption = message.caption[:1000] if message.caption else None
            existing_message.mark_as_edited(message.edit_date)

            await session.commit()
            logger.debug(f"更新了私聊编辑消息: 用户={message.chat.id}, 消息ID={message.message_id}")

    except Exception as e:
        logger.exception(f"处理私聊编辑消息时发生错误: {e}")
        await session.rollback()
