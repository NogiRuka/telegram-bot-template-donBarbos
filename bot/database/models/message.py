from __future__ import annotations
import datetime
from enum import Enum

from sqlalchemy import String, Text, Index, BigInteger, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, big_int_pk, created_at


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    DOCUMENT = "document"
    STICKER = "sticker"
    ANIMATION = "animation"
    LOCATION = "location"
    CONTACT = "contact"
    POLL = "poll"
    DICE = "dice"
    GAME = "game"
    INVOICE = "invoice"
    SUCCESSFUL_PAYMENT = "successful_payment"
    OTHER = "other"


class MessageModel(Base):
    """
    消息记录模型类，用于存储用户消息统计信息
    
    字段说明：
    - id: 消息ID（自增主键）
    - message_id: Telegram消息ID
    - user_id: 发送用户ID
    - chat_id: 聊天ID
    - message_type: 消息类型
    - text_content: 文本内容（截取前1000字符）
    - file_id: 文件ID（如果是媒体消息）
    - file_size: 文件大小
    - created_at: 消息创建时间
    - is_forwarded: 是否为转发消息
    - is_reply: 是否为回复消息
    - reply_to_message_id: 回复的消息ID
    """
    __tablename__ = "messages"

    # 主键（自增）
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Telegram相关ID
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    
    # 消息内容
    message_type: Mapped[MessageType] = mapped_column(SQLEnum(MessageType), nullable=False, index=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    
    # 时间戳
    created_at: Mapped[created_at]
    
    # 消息属性
    is_forwarded: Mapped[bool] = mapped_column(default=False)
    is_reply: Mapped[bool] = mapped_column(default=False)
    reply_to_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    # 索引定义
    __table_args__ = (
        Index('idx_messages_user_created', 'user_id', 'created_at'),
        Index('idx_messages_chat_created', 'chat_id', 'created_at'),
        Index('idx_messages_type_created', 'message_type', 'created_at'),
        Index('idx_messages_telegram_id', 'message_id', 'chat_id'),
    )
    
    # 用于repr显示的列
    repr_cols = ('id', 'user_id', 'message_type', 'created_at')