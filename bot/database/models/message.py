"""
消息记录模型模块

本模块定义了Telegram消息的数据库模型，
用于存储和管理用户发送的各种类型消息。

作者: Telegram Bot Template
创建时间: 2024-01-23
最后更新: 2025-10-21
"""

from __future__ import annotations
import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, Index, BigInteger, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class MessageType(str, Enum):
    """
    消息类型枚举
    
    定义了Telegram支持的各种消息类型，
    用于分类和统计不同类型的消息。
    """
    
    TEXT = "text"                          # 文本消息，包含纯文本内容
    PHOTO = "photo"                        # 图片消息，包含图片文件
    VIDEO = "video"                        # 视频消息，包含视频文件
    AUDIO = "audio"                        # 音频消息，包含音频文件
    VOICE = "voice"                        # 语音消息，包含语音录音
    DOCUMENT = "document"                  # 文档消息，包含各种文档文件
    STICKER = "sticker"                    # 贴纸消息，包含表情贴纸
    ANIMATION = "animation"                # 动画消息，包含GIF等动画
    LOCATION = "location"                  # 位置消息，包含地理位置信息
    CONTACT = "contact"                    # 联系人消息，包含联系人信息
    POLL = "poll"                          # 投票消息，包含投票内容
    DICE = "dice"                          # 骰子消息，包含随机数字
    GAME = "game"                          # 游戏消息，包含游戏内容
    INVOICE = "invoice"                    # 发票消息，包含支付信息
    SUCCESSFUL_PAYMENT = "successful_payment"  # 支付成功消息
    VIDEO_NOTE = "video_note"              # 视频笔记消息，圆形视频
    VENUE = "venue"                        # 场所消息，包含场所信息
    WEB_APP_DATA = "web_app_data"          # Web应用数据消息
    PASSPORT_DATA = "passport_data"        # 护照数据消息
    PROXIMITY_ALERT = "proximity_alert"    # 接近警报消息
    FORUM_TOPIC_CREATED = "forum_topic_created"      # 论坛主题创建消息
    FORUM_TOPIC_EDITED = "forum_topic_edited"        # 论坛主题编辑消息
    FORUM_TOPIC_CLOSED = "forum_topic_closed"        # 论坛主题关闭消息
    FORUM_TOPIC_REOPENED = "forum_topic_reopened"    # 论坛主题重开消息
    GENERAL_FORUM_TOPIC_HIDDEN = "general_forum_topic_hidden"    # 通用论坛主题隐藏消息
    GENERAL_FORUM_TOPIC_UNHIDDEN = "general_forum_topic_unhidden"  # 通用论坛主题显示消息
    VIDEO_CHAT_SCHEDULED = "video_chat_scheduled"    # 视频聊天安排消息
    VIDEO_CHAT_STARTED = "video_chat_started"        # 视频聊天开始消息
    VIDEO_CHAT_ENDED = "video_chat_ended"            # 视频聊天结束消息
    VIDEO_CHAT_PARTICIPANTS_INVITED = "video_chat_participants_invited"  # 视频聊天邀请消息
    OTHER = "other"                        # 其他类型消息，未分类的消息类型


class MessageModel(Base, BasicAuditMixin):
    """
    消息记录模型类
    
    存储Telegram机器人接收到的所有消息记录，
    用于消息统计、分析和审计功能。
    
    继承自:
        Base: 基础模型类，提供通用功能
        BasicAuditMixin: 基础审计混入，提供时间戳、操作者和软删除字段
    
    主要功能:
        1. 记录用户发送的各种类型消息
        2. 存储消息的基本信息和内容摘要
        3. 支持消息的转发和回复关系追踪
        4. 提供消息统计和分析的数据基础
        5. 支持消息的搜索和过滤功能
    
    数据库表名: messages
    """
    
    __tablename__ = "messages"

    # ==================== 主键字段 ====================
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True, 
        autoincrement=True,
        comment="消息记录ID，自增主键，唯一标识一条消息记录"
    )
    
    # ==================== Telegram标识字段 ====================
    
    message_id: Mapped[int] = mapped_column(
        BigInteger, 
        nullable=False, 
        index=True,
        comment="Telegram消息ID，必填字段，Telegram平台的原始消息标识符"
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, 
        nullable=False, 
        index=True,
        comment="发送用户ID，必填字段，消息发送者的Telegram用户ID"
    )
    
    chat_id: Mapped[int] = mapped_column(
        BigInteger, 
        nullable=False, 
        index=True,
        comment="聊天ID，必填字段，消息所在聊天的Telegram聊天ID"
    )
    
    # ==================== 消息内容字段 ====================
    
    message_type: Mapped[MessageType] = mapped_column(
        SQLEnum(MessageType), 
        nullable=False, 
        index=True,
        comment="消息类型，必填字段，使用MessageType枚举值标识消息的具体类型"
    )
    
    text_content: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="文本内容，可选字段，存储消息的文本内容，对于长消息会截取前1000字符"
    )
    
    caption: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="媒体说明，可选字段，存储图片、视频等媒体消息的说明文字"
    )
    
    entities: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="消息实体，可选字段，存储消息格式化信息的JSON字符串（链接、提及、粗体等）"
    )
    
    caption_entities: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="媒体说明实体，可选字段，存储媒体说明格式化信息的JSON字符串"
    )
    
    # ==================== 文件信息字段 ====================
    
    file_id: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True, 
        index=True,
        comment="文件ID，可选字段，Telegram文件的唯一标识符，用于媒体消息"
    )
    
    file_unique_id: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="文件唯一ID，可选字段，Telegram文件的永久唯一标识符"
    )
    
    file_size: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True,
        comment="文件大小，可选字段，文件的字节大小，用于存储统计"
    )
    
    file_name: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="文件名称，可选字段，原始文件的名称"
    )
    
    mime_type: Mapped[str | None] = mapped_column(
        String(100), 
        nullable=True,
        comment="MIME类型，可选字段，文件的媒体类型标识"
    )
    
    # ==================== 消息关系字段 ====================
    
    is_forwarded: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="是否转发，默认False，True表示此消息是从其他聊天转发而来"
    )
    
    forward_from_user_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True,
        comment="转发来源用户ID，可选字段，原始消息发送者的用户ID"
    )
    
    forward_from_chat_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True,
        comment="转发来源聊天ID，可选字段，原始消息所在聊天的ID"
    )
    
    forward_from_message_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True,
        comment="转发来源消息ID，可选字段，原始消息的消息ID"
    )
    
    is_reply: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="是否回复，默认False，True表示此消息是对其他消息的回复"
    )
    
    reply_to_message_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True, 
        index=True,
        comment="回复目标消息ID，可选字段，被回复消息的Telegram消息ID"
    )
    
    reply_to_user_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True,
        comment="回复目标用户ID，可选字段，被回复消息的发送者用户ID"
    )
    
    # ==================== 消息状态字段 ====================
    
    is_edited: Mapped[bool] = mapped_column(
        default=False,
        comment="是否已编辑，默认False，True表示此消息已被用户编辑过"
    )
    
    edit_date: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True,
        comment="编辑时间，可选字段，消息最后编辑的时间"
    )
    
    # 注意：is_deleted 和 deleted_at 字段已由 BasicAuditMixin 提供
    
    # ==================== 统计字段 ====================
    
    character_count: Mapped[int] = mapped_column(
        default=0,
        comment="字符数量，默认0，消息文本内容的字符数统计"
    )
    
    word_count: Mapped[int] = mapped_column(
        default=0,
        comment="单词数量，默认0，消息文本内容的单词数统计"
    )
    
    # ==================== 元数据字段 ====================
    
    language_code: Mapped[str | None] = mapped_column(
        String(10), 
        nullable=True,
        comment="语言代码，可选字段，检测到的消息文本语言代码"
    )
    
    sentiment_score: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="情感分数，可选字段，消息情感分析的分数，范围-1到1"
    )
    
    # ==================== 数据库索引定义 ====================
    
    __table_args__ = (
        # 索引定义 - 用于提高查询性能和支持复杂查询
        Index('idx_messages_user_created', 'user_id', 'created_at'),  # 用户消息时间索引，用于查询特定用户的消息历史
        Index('idx_messages_chat_created', 'chat_id', 'created_at'),  # 聊天消息时间索引，用于查询特定聊天的消息历史
        Index('idx_messages_type_created', 'message_type', 'created_at'),  # 消息类型时间索引，用于按消息类型进行统计分析
        Index('idx_messages_telegram_unique', 'message_id', 'chat_id', unique=True),  # Telegram消息唯一索引，确保同一聊天中的消息ID唯一
        Index('idx_messages_forward', 'is_forwarded', 'forward_from_user_id'),  # 转发消息索引，用于查询消息的转发关系
        Index('idx_messages_reply', 'is_reply', 'reply_to_message_id'),  # 回复消息索引，用于查询消息的回复关系
        Index('idx_messages_file', 'file_id', 'message_type'),  # 文件消息索引，用于查询包含文件的消息
        Index('idx_messages_edited', 'is_edited', 'edit_date'),  # 编辑状态索引，用于查询已编辑的消息
        # 注意：删除状态索引已由 BasicAuditMixin 提供
        Index('idx_messages_user_chat', 'user_id', 'chat_id', 'created_at'),  # 用户聊天组合索引，用于查询用户在特定聊天中的消息
        Index('idx_messages_lang_sentiment', 'language_code', 'sentiment_score'),  # 语言情感索引，用于多语言消息分析和情感统计
    )
    
    # ==================== 显示配置 ====================
    
    # 用于__repr__方法显示的关键列
    repr_cols = ('id', 'user_id', 'chat_id', 'message_type', 'created_at', 'is_deleted')
    
    # ==================== 业务方法 ====================
    
    def get_content_preview(self, max_length: int = 50) -> str:
        """
        获取消息内容预览
        
        返回消息内容的简短预览，用于列表显示。
        
        参数:
            max_length: 最大长度，默认50个字符
            
        返回:
            str: 消息内容预览
        """
        if self.text_content:
            content = self.text_content.strip()
            if len(content) > max_length:
                return content[:max_length] + "..."
            return content
        elif self.caption:
            content = self.caption.strip()
            if len(content) > max_length:
                return content[:max_length] + "..."
            return content
        else:
            return f"[{self.message_type.value}]"
    
    def get_display_type(self) -> str:
        """
        获取消息类型的显示名称
        
        返回适合在界面中显示的消息类型名称。
        
        返回:
            str: 消息类型显示名称
        """
        type_names = {
            MessageType.TEXT: "文本",
            MessageType.PHOTO: "图片",
            MessageType.VIDEO: "视频",
            MessageType.AUDIO: "音频",
            MessageType.VOICE: "语音",
            MessageType.DOCUMENT: "文档",
            MessageType.STICKER: "贴纸",
            MessageType.ANIMATION: "动画",
            MessageType.LOCATION: "位置",
            MessageType.CONTACT: "联系人",
            MessageType.POLL: "投票",
            MessageType.DICE: "骰子",
            MessageType.GAME: "游戏",
            MessageType.INVOICE: "发票",
            MessageType.SUCCESSFUL_PAYMENT: "支付成功",
            MessageType.VIDEO_NOTE: "视频笔记",
            MessageType.VENUE: "场所",
            MessageType.WEB_APP_DATA: "Web应用数据",
            MessageType.OTHER: "其他"
        }
        return type_names.get(self.message_type, "未知")
    
    def is_media_message(self) -> bool:
        """
        判断是否为媒体消息
        
        返回:
            bool: True表示是媒体消息，False表示不是
        """
        media_types = {
            MessageType.PHOTO, MessageType.VIDEO, MessageType.AUDIO,
            MessageType.VOICE, MessageType.DOCUMENT, MessageType.STICKER,
            MessageType.ANIMATION, MessageType.VIDEO_NOTE
        }
        return self.message_type in media_types
    
    def get_file_size_display(self) -> str:
        """
        获取文件大小的显示格式
        
        返回:
            str: 格式化的文件大小字符串
        """
        if not self.file_size:
            return "未知"
        
        size = self.file_size
        units = ['B', 'KB', 'MB', 'GB']
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
    
    def update_statistics(self) -> None:
        """
        更新消息统计信息
        
        计算并更新字符数、单词数等统计字段。
        """
        content = self.text_content or self.caption or ""
        
        # 更新字符数
        self.character_count = len(content)
        
        # 更新单词数（简单按空格分割）
        if content.strip():
            self.word_count = len(content.split())
        else:
            self.word_count = 0
    
    def mark_as_edited(self, edit_time: datetime.datetime | None = None) -> None:
        """
        标记消息为已编辑
        
        参数:
            edit_time: 编辑时间，如果不提供则使用当前时间
        """
        self.is_edited = True
        self.edit_date = edit_time or datetime.datetime.utcnow()
    
    def soft_delete(self, delete_time: datetime.datetime | None = None) -> None:
        """
        软删除消息
        
        参数:
            delete_time: 删除时间，如果不提供则使用当前时间
        """
        self.is_deleted = True
        self.deleted_at = delete_time or datetime.datetime.utcnow()
    
    def restore(self) -> None:
        """
        恢复已删除的消息
        """
        self.is_deleted = False
        self.deleted_at = None
    
    def get_sentiment_display(self) -> str:
        """
        获取情感分析结果的显示文本
        
        返回:
            str: 情感分析结果的中文描述
        """
        if self.sentiment_score is None:
            return "未分析"
        
        if self.sentiment_score > 0.1:
            return "积极"
        elif self.sentiment_score < -0.1:
            return "消极"
        else:
            return "中性"
    
    def get_formatted_text(self) -> str:
        """
        获取格式化的文本内容
        
        根据存储的entities信息，将纯文本转换为包含格式化标记的文本。
        
        返回:
            str: 格式化的文本内容
        """
        import json
        
        text = self.text_content or ""
        if not text or not self.entities:
            return text
        
        try:
            entities = json.loads(self.entities)
            if not entities:
                return text
            
            # 按offset倒序排列，从后往前处理，避免位置偏移
            entities.sort(key=lambda x: x.get('offset', 0), reverse=True)
            
            formatted_text = text
            for entity in entities:
                entity_type = entity.get('type')
                offset = entity.get('offset', 0)
                length = entity.get('length', 0)
                
                if offset + length > len(formatted_text):
                    continue
                
                entity_text = formatted_text[offset:offset + length]
                
                # 根据实体类型添加格式化标记
                if entity_type == 'bold':
                    replacement = f"**{entity_text}**"
                elif entity_type == 'italic':
                    replacement = f"*{entity_text}*"
                elif entity_type == 'code':
                    replacement = f"`{entity_text}`"
                elif entity_type == 'pre':
                    replacement = f"```{entity_text}```"
                elif entity_type == 'url':
                    replacement = f"[{entity_text}]({entity_text})"
                elif entity_type == 'text_link':
                    url = entity.get('url', entity_text)
                    replacement = f"[{entity_text}]({url})"
                elif entity_type == 'mention':
                    replacement = entity_text  # 保持原样，因为已经包含@
                elif entity_type == 'text_mention':
                    user = entity.get('user', {})
                    username = user.get('username', user.get('first_name', entity_text))
                    replacement = f"[@{username}](tg://user?id={user.get('id', '')})"
                elif entity_type == 'hashtag':
                    replacement = entity_text  # 保持原样，因为已经包含#
                elif entity_type == 'cashtag':
                    replacement = entity_text  # 保持原样，因为已经包含$
                elif entity_type == 'strikethrough':
                    replacement = f"~~{entity_text}~~"
                elif entity_type == 'underline':
                    replacement = f"__{entity_text}__"
                elif entity_type == 'spoiler':
                    replacement = f"||{entity_text}||"
                else:
                    replacement = entity_text
                
                # 替换文本
                formatted_text = formatted_text[:offset] + replacement + formatted_text[offset + length:]
            
            return formatted_text
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # 如果解析失败，返回原始文本
            return text
    
    def get_formatted_caption(self) -> str:
        """
        获取格式化的媒体说明
        
        根据存储的caption_entities信息，将纯文本转换为包含格式化标记的文本。
        
        返回:
            str: 格式化的媒体说明
        """
        import json
        
        caption = self.caption or ""
        if not caption or not self.caption_entities:
            return caption
        
        try:
            entities = json.loads(self.caption_entities)
            if not entities:
                return caption
            
            # 按offset倒序排列，从后往前处理，避免位置偏移
            entities.sort(key=lambda x: x.get('offset', 0), reverse=True)
            
            formatted_caption = caption
            for entity in entities:
                entity_type = entity.get('type')
                offset = entity.get('offset', 0)
                length = entity.get('length', 0)
                
                if offset + length > len(formatted_caption):
                    continue
                
                entity_text = formatted_caption[offset:offset + length]
                
                # 根据实体类型添加格式化标记
                if entity_type == 'bold':
                    replacement = f"**{entity_text}**"
                elif entity_type == 'italic':
                    replacement = f"*{entity_text}*"
                elif entity_type == 'code':
                    replacement = f"`{entity_text}`"
                elif entity_type == 'pre':
                    replacement = f"```{entity_text}```"
                elif entity_type == 'url':
                    replacement = f"[{entity_text}]({entity_text})"
                elif entity_type == 'text_link':
                    url = entity.get('url', entity_text)
                    replacement = f"[{entity_text}]({url})"
                elif entity_type == 'mention':
                    replacement = entity_text  # 保持原样，因为已经包含@
                elif entity_type == 'text_mention':
                    user = entity.get('user', {})
                    username = user.get('username', user.get('first_name', entity_text))
                    replacement = f"[@{username}](tg://user?id={user.get('id', '')})"
                elif entity_type == 'hashtag':
                    replacement = entity_text  # 保持原样，因为已经包含#
                elif entity_type == 'cashtag':
                    replacement = entity_text  # 保持原样，因为已经包含$
                elif entity_type == 'strikethrough':
                    replacement = f"~~{entity_text}~~"
                elif entity_type == 'underline':
                    replacement = f"__{entity_text}__"
                elif entity_type == 'spoiler':
                    replacement = f"||{entity_text}||"
                else:
                    replacement = entity_text
                
                # 替换文本
                formatted_caption = formatted_caption[:offset] + replacement + formatted_caption[offset + length:]
            
            return formatted_caption
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # 如果解析失败，返回原始文本
            return caption
    
    @classmethod
    def create_from_telegram(
        cls,
        message_id: int,
        user_id: int,
        chat_id: int,
        message_type: MessageType,
        text_content: str | None = None,
        caption: str | None = None,
        entities: str | None = None,
        caption_entities: str | None = None,
        file_id: str | None = None,
        file_size: int | None = None,
        **kwargs
    ) -> "MessageModel":
        """
        从Telegram消息创建消息记录
        
        便捷方法用于从Telegram API接收的消息创建数据库记录。
        
        参数:
            message_id: Telegram消息ID
            user_id: 发送用户ID
            chat_id: 聊天ID
            message_type: 消息类型
            text_content: 文本内容，可选
            caption: 媒体说明，可选
            entities: 消息格式化实体JSON字符串，可选
            caption_entities: 媒体说明格式化实体JSON字符串，可选
            file_id: 文件ID，可选
            file_size: 文件大小，可选
            **kwargs: 其他字段参数
            
        返回:
            MessageModel: 新创建的消息实例
        """
        message = cls(
            message_id=message_id,
            user_id=user_id,
            chat_id=chat_id,
            message_type=message_type,
            text_content=text_content,
            caption=caption,
            entities=entities,
            caption_entities=caption_entities,
            file_id=file_id,
            file_size=file_size,
            **kwargs
        )
        
        # 更新统计信息
        message.update_statistics()
        
        return message