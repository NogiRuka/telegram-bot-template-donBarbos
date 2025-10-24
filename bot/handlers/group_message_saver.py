"""
群组消息保存处理器模块

本模块实现了自动保存群组消息的功能，
根据群组配置自动保存符合条件的消息到数据库。

作者: Telegram Bot Template
创建时间: 2025-01-21
最后更新: 2025-01-21
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from aiogram import types, Router, F
from aiogram.enums import ChatType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 移除db_session导入，使用依赖注入
from bot.database.models import (
    MessageModel, MessageType, 
    GroupConfigModel, GroupType, MessageSaveMode
)
from bot.services.analytics import analytics

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = Router()


class GroupMessageSaver:
    """
    群组消息保存器类
    
    负责处理群组消息的自动保存功能，
    根据群组配置决定是否保存消息。
    """
    
    def __init__(self):
        self.message_type_mapping = {
            "text": MessageType.TEXT,
            "photo": MessageType.PHOTO,
            "video": MessageType.VIDEO,
            "audio": MessageType.AUDIO,
            "voice": MessageType.VOICE,
            "document": MessageType.DOCUMENT,
            "sticker": MessageType.STICKER,
            "animation": MessageType.ANIMATION,
            "location": MessageType.LOCATION,
            "contact": MessageType.CONTACT,
            "poll": MessageType.POLL,
            "dice": MessageType.DICE,
            "game": MessageType.GAME,
            "invoice": MessageType.INVOICE,
            "successful_payment": MessageType.SUCCESSFUL_PAYMENT,
            "video_note": MessageType.VIDEO_NOTE,
            "venue": MessageType.VENUE,
            "web_app_data": MessageType.WEB_APP_DATA,
        }
    
    async def get_group_config(self, chat_id: int, session: AsyncSession) -> Optional[GroupConfigModel]:
        """
        获取群组配置
        
        Args:
            chat_id: 群组聊天ID
            session: 数据库会话
            
        Returns:
            GroupConfigModel: 群组配置，如果不存在则返回None
        """
        try:
            result = await session.execute(
                select(GroupConfigModel).where(
                    GroupConfigModel.chat_id == chat_id,
                    GroupConfigModel.is_deleted == False
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取群组配置失败: {e}")
            return None
    
    async def create_default_config(self, chat: types.Chat, session: AsyncSession) -> Optional[GroupConfigModel]:
        """
        为新群组创建默认配置
        
        Args:
            chat: Telegram聊天对象
            session: 数据库会话
            
        Returns:
            GroupConfigModel: 创建的群组配置
        """
        try:
            # 确定群组类型
            if chat.type == "group":
                group_type = GroupType.GROUP
            elif chat.type == "supergroup":
                group_type = GroupType.SUPERGROUP
            elif chat.type == "channel":
                group_type = GroupType.CHANNEL
            else:
                logger.warning(f"未知的聊天类型: {chat.type}")
                return None
            
            # 创建默认配置（默认禁用消息保存）
            config = GroupConfigModel.create_for_group(
                chat_id=chat.id,
                chat_title=chat.title,
                chat_username=chat.username,
                group_type=group_type,
                is_message_save_enabled=False,  # 默认禁用
                message_save_mode=MessageSaveMode.DISABLED
            )
            
            session.add(config)
            await session.commit()
            
            logger.info(f"为群组 {chat.id} 创建了默认配置")
            return config
            
        except Exception as e:
            logger.error(f"创建群组默认配置失败: {e}")
            await session.rollback()
            return None
    
    def get_message_type(self, message: types.Message) -> MessageType:
        """
        获取消息类型
        
        Args:
            message: Telegram消息对象
            
        Returns:
            MessageType: 消息类型枚举值
        """
        # 检查各种消息类型
        if message.photo:
            return MessageType.PHOTO
        elif message.video:
            return MessageType.VIDEO
        elif message.audio:
            return MessageType.AUDIO
        elif message.voice:
            return MessageType.VOICE
        elif message.document:
            return MessageType.DOCUMENT
        elif message.sticker:
            return MessageType.STICKER
        elif message.animation:
            return MessageType.ANIMATION
        elif message.location:
            return MessageType.LOCATION
        elif message.contact:
            return MessageType.CONTACT
        elif message.poll:
            return MessageType.POLL
        elif message.dice:
            return MessageType.DICE
        elif message.game:
            return MessageType.GAME
        elif message.invoice:
            return MessageType.INVOICE
        elif message.successful_payment:
            return MessageType.SUCCESSFUL_PAYMENT
        elif message.video_note:
            return MessageType.VIDEO_NOTE
        elif message.venue:
            return MessageType.VENUE
        elif message.web_app_data:
            return MessageType.WEB_APP_DATA
        elif message.text:
            return MessageType.TEXT
        else:
            return MessageType.OTHER
    
    def extract_file_info(self, message: types.Message) -> Dict[str, Any]:
        """
        提取文件信息
        
        Args:
            message: Telegram消息对象
            
        Returns:
            Dict: 文件信息字典
        """
        file_info = {
            "file_id": None,
            "file_unique_id": None,
            "file_size": None,
            "file_name": None,
            "mime_type": None
        }
        
        # 根据消息类型提取文件信息
        if message.photo:
            # 选择最大尺寸的图片
            largest_photo = max(message.photo, key=lambda x: x.file_size or 0)
            file_info.update({
                "file_id": largest_photo.file_id,
                "file_unique_id": largest_photo.file_unique_id,
                "file_size": largest_photo.file_size
            })
        elif message.video:
            file_info.update({
                "file_id": message.video.file_id,
                "file_unique_id": message.video.file_unique_id,
                "file_size": message.video.file_size,
                "file_name": message.video.file_name,
                "mime_type": message.video.mime_type
            })
        elif message.audio:
            file_info.update({
                "file_id": message.audio.file_id,
                "file_unique_id": message.audio.file_unique_id,
                "file_size": message.audio.file_size,
                "file_name": message.audio.file_name,
                "mime_type": message.audio.mime_type
            })
        elif message.voice:
            file_info.update({
                "file_id": message.voice.file_id,
                "file_unique_id": message.voice.file_unique_id,
                "file_size": message.voice.file_size,
                "mime_type": message.voice.mime_type
            })
        elif message.document:
            file_info.update({
                "file_id": message.document.file_id,
                "file_unique_id": message.document.file_unique_id,
                "file_size": message.document.file_size,
                "file_name": message.document.file_name,
                "mime_type": message.document.mime_type
            })
        elif message.sticker:
            file_info.update({
                "file_id": message.sticker.file_id,
                "file_unique_id": message.sticker.file_unique_id,
                "file_size": message.sticker.file_size
            })
        elif message.animation:
            file_info.update({
                "file_id": message.animation.file_id,
                "file_unique_id": message.animation.file_unique_id,
                "file_size": message.animation.file_size,
                "file_name": message.animation.file_name,
                "mime_type": message.animation.mime_type
            })
        elif message.video_note:
            file_info.update({
                "file_id": message.video_note.file_id,
                "file_unique_id": message.video_note.file_unique_id,
                "file_size": message.video_note.file_size
            })
        
        return file_info
    
    def check_keywords(self, text: str, include_keywords: Optional[str], 
                      exclude_keywords: Optional[str]) -> bool:
        """
        检查关键词过滤
        
        Args:
            text: 要检查的文本
            include_keywords: 包含关键词JSON字符串
            exclude_keywords: 排除关键词JSON字符串
            
        Returns:
            bool: True表示通过关键词过滤
        """
        if not text:
            return True
            
        text_lower = text.lower()
        
        # 检查包含关键词
        if include_keywords:
            try:
                keywords = json.loads(include_keywords)
                if keywords and not any(keyword.lower() in text_lower for keyword in keywords):
                    return False
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"无效的包含关键词JSON: {include_keywords}")
        
        # 检查排除关键词
        if exclude_keywords:
            try:
                keywords = json.loads(exclude_keywords)
                if keywords and any(keyword.lower() in text_lower for keyword in keywords):
                    return False
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"无效的排除关键词JSON: {exclude_keywords}")
        
        return True
    
    def extract_entities(self, entities: Optional[List]) -> Optional[str]:
        """
        提取消息实体信息并转换为JSON字符串
        
        Args:
            entities: Telegram消息实体列表
            
        Returns:
            str: JSON格式的实体信息，如果没有实体则返回None
        """
        if not entities:
            return None
        
        try:
            entities_data = []
            for entity in entities:
                entity_dict = {
                    "type": entity.type,
                    "offset": entity.offset,
                    "length": entity.length
                }
                
                # 根据实体类型添加额外信息
                if entity.type == "url":
                    entity_dict["url"] = entity.url if hasattr(entity, 'url') else None
                elif entity.type == "text_link":
                    entity_dict["url"] = entity.url if hasattr(entity, 'url') else None
                elif entity.type == "text_mention":
                    if hasattr(entity, 'user') and entity.user:
                        entity_dict["user"] = {
                            "id": entity.user.id,
                            "first_name": entity.user.first_name,
                            "last_name": entity.user.last_name,
                            "username": entity.user.username
                        }
                elif entity.type == "mention":
                    # @username 提及
                    pass
                elif entity.type in ["bold", "italic", "underline", "strikethrough", "spoiler", "code", "pre"]:
                    # 格式化实体
                    if entity.type == "pre" and hasattr(entity, 'language'):
                        entity_dict["language"] = entity.language
                
                entities_data.append(entity_dict)
            
            return json.dumps(entities_data, ensure_ascii=False) if entities_data else None
            
        except Exception as e:
            logger.error(f"提取实体信息失败: {e}")
            return None
    
    async def save_message(self, message: types.Message, config: GroupConfigModel, 
                          session: AsyncSession) -> bool:
        """
        保存消息到数据库
        
        Args:
            message: Telegram消息对象
            config: 群组配置
            session: 数据库会话
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 获取消息类型
            message_type = self.get_message_type(message)
            
            # 检查是否应该保存此消息
            is_forwarded = message.forward_from is not None or message.forward_from_chat is not None
            is_reply = message.reply_to_message is not None
            is_from_bot = message.from_user and message.from_user.is_bot
            
            if not config.should_save_message(
                message_type=message_type.value,
                is_forwarded=is_forwarded,
                is_reply=is_reply,
                is_from_bot=is_from_bot
            ):
                return False
            
            # 检查关键词过滤
            text_content = message.text or message.caption or ""
            if not self.check_keywords(text_content, config.include_keywords, config.exclude_keywords):
                return False
            
            # 提取文件信息
            file_info = self.extract_file_info(message)
            
            # 检查文件大小限制
            if (config.max_file_size_mb and file_info["file_size"] and 
                file_info["file_size"] > config.max_file_size_mb * 1024 * 1024):
                logger.info(f"消息 {message.message_id} 文件大小超过限制，跳过保存")
                return False
            
            # 提取消息实体信息
            entities_json = self.extract_entities(message.entities) if message.entities else None
            caption_entities_json = self.extract_entities(message.caption_entities) if message.caption_entities else None
            
            # 创建消息记录
            message_record = MessageModel.create_from_telegram(
                message_id=message.message_id,
                user_id=message.from_user.id if message.from_user else 0,
                chat_id=message.chat.id,
                message_type=message_type,
                text_content=text_content[:1000] if text_content else None,  # 限制长度
                caption=message.caption[:1000] if message.caption else None,
                entities=entities_json,
                caption_entities=caption_entities_json,
                file_id=file_info["file_id"],
                file_unique_id=file_info["file_unique_id"],
                file_size=file_info["file_size"],
                file_name=file_info["file_name"],
                mime_type=file_info["mime_type"],
                is_forwarded=is_forwarded,
                is_reply=is_reply
            )
            
            # 设置转发信息
            if is_forwarded:
                if message.forward_from:
                    message_record.forward_from_user_id = message.forward_from.id
                elif message.forward_from_chat:
                    message_record.forward_from_chat_id = message.forward_from_chat.id
                if hasattr(message, 'forward_from_message_id'):
                    message_record.forward_from_message_id = message.forward_from_message_id
            
            # 设置回复信息
            if is_reply and message.reply_to_message:
                message_record.reply_to_message_id = message.reply_to_message.message_id
                if message.reply_to_message.from_user:
                    message_record.reply_to_user_id = message.reply_to_message.from_user.id
            
            # 保存到数据库
            session.add(message_record)
            
            # 更新群组配置统计
            config.increment_message_count(message_record.created_at)
            
            await session.commit()
            
            logger.debug(f"成功保存消息: 群组={message.chat.id}, 消息ID={message.message_id}, 类型={message_type.value}")
            
            # 分析事件通过装饰器自动处理
            
            return True
            
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            await session.rollback()
            return False


# 创建消息保存器实例
message_saver = GroupMessageSaver()


@router.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]))
async def handle_group_message(message: types.Message, session: AsyncSession) -> None:
    """
    处理群组消息
    
    自动检查群组配置并保存符合条件的消息。
    
    Args:
        message: Telegram消息对象
        session: 数据库会话
    """
    try:
        # 获取群组配置
        config = await message_saver.get_group_config(message.chat.id, session)
        
        # 如果没有配置，创建默认配置
        if not config:
            config = await message_saver.create_default_config(message.chat, session)
            if not config:
                return
        
        # 如果启用了消息保存，则保存消息
        if config.is_save_enabled():
            success = await message_saver.save_message(message, config, session)
            if success:
                logger.debug(f"群组 {message.chat.id} 的消息已保存")
        
    except Exception as e:
        logger.error(f"处理群组消息时发生错误: {e}")


@router.edited_message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]))
async def handle_edited_group_message(message: types.Message, session: AsyncSession) -> None:
    """
    处理群组编辑消息
    
    更新已保存的消息记录。
    
    Args:
        message: 编辑后的Telegram消息对象
        session: 数据库会话
    """
    try:
        # 查找原始消息记录
        result = await session.execute(
            select(MessageModel).where(
                MessageModel.message_id == message.message_id,
                MessageModel.chat_id == message.chat.id,
                MessageModel.is_deleted == False
            )
        )
        
        existing_message = result.scalar_one_or_none()
        
        if existing_message:
            # 更新消息内容
            existing_message.text_content = (message.text or message.caption or "")[:1000]
            existing_message.caption = message.caption[:1000] if message.caption else None
            existing_message.mark_as_edited(message.edit_date)
            
            await session.commit()
            logger.debug(f"更新了编辑消息: 群组={message.chat.id}, 消息ID={message.message_id}")
            
    except Exception as e:
        logger.error(f"处理编辑消息时发生错误: {e}")
        await session.rollback()


# 导出路由器
__all__ = ["router", "GroupMessageSaver", "message_saver"]