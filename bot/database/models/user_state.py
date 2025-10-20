from __future__ import annotations
import datetime

from sqlalchemy import String, Text, Index, BigInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, created_at, updated_at


class UserStateModel(Base):
    """
    用户会话状态模型类，用于存储FSM状态信息
    
    字段说明：
    - user_id: 用户ID（主键）
    - chat_id: 聊天ID
    - state: 当前状态
    - data: 状态数据（JSON格式）
    - created_at: 创建时间
    - updated_at: 更新时间
    - expires_at: 过期时间
    """
    __tablename__ = "user_states"

    # 复合主键
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # 状态信息
    state: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # 时间戳
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
    expires_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True, index=True)
    
    # 索引定义
    __table_args__ = (
        Index('idx_user_states_state', 'state'),
        Index('idx_user_states_expires', 'expires_at'),
        Index('idx_user_states_updated', 'updated_at'),
    )
    
    # 用于repr显示的列
    repr_cols = ('user_id', 'chat_id', 'state', 'updated_at')