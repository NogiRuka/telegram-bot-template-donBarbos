"""
经济系统模型模块

本模块定义了经济系统相关的数据库模型，
包括货币流水、动态配置和商品信息。
"""

from datetime import datetime as dt
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk, big_int_pk


class CurrencyTransactionModel(Base, BasicAuditMixin):
    """货币流水模型
    
    功能说明:
    - 记录用户的每一次代币获取和消耗，用于审计和回溯。
    
    字段:
    - id: 流水ID (BigInt, PK)
    - user_id: 用户ID (BigInt, FK users.id)
    - amount: 变动数值 (正数为获取，负数为消耗)
    - balance_after: 变动后余额 (快照)
    - event_type: 事件类型 (daily_checkin, redeem_emby 等)
    - description: 流水描述 (人类可读)
    - meta: 扩展信息 (JSON)
    """
    
    __tablename__ = "currency_transactions"
    
    id: Mapped[big_int_pk] = mapped_column(primary_key=True, autoincrement=True, comment="流水ID")
    
    user_id: Mapped[int] = mapped_column(index=True, nullable=False, comment="关联 users.id")
    
    amount: Mapped[int] = mapped_column(nullable=False, comment="变动数值")
    
    balance_after: Mapped[int] = mapped_column(nullable=False, comment="变动后余额")
    
    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="事件类型")
    
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="流水描述")
    
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展信息")
    
    __table_args__ = (
        Index("idx_currency_trans_user_event", "user_id", "event_type"),
    )


class CurrencyConfigModel(Base, BasicAuditMixin):
    """经济系统配置模型
    
    功能说明:
    - 存储经济系统的动态配置，如签到奖励基数、连签加成等。
    
    字段:
    - id: 配置ID (Auto Int)
    - config_key: 配置键名 (Unique)
    - value: 数值
    - description: 说明
    """
    
    __tablename__ = "currency_config"
    
    id: Mapped[auto_int_pk]
    
    config_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="配置键名")
    
    value: Mapped[int] = mapped_column(nullable=False, comment="数值")
    
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="配置说明")


class CurrencyProductModel(Base, BasicAuditMixin):
    """商品模型
    
    功能说明:
    - 存储商店可售卖的商品信息。
    
    字段:
    - id: 商品ID (Auto Int)
    - name: 商品名称
    - description: 商品描述
    - price: 价格
    - category: 分类 (tools, emby, group)
    - action_type: 行为类型 (retro_checkin, emby_image, custom_title)
    - reward_value: 实际效果参数 (JSON)
    - stock: 库存 (-1表示无限)
    - visible_conditions: 可见条件 (JSON)
    - purchase_conditions: 购买条件 (JSON)
    - start_time: 上架时间
    - end_time: 下架时间
    - is_active: 是否上架
    """
    
    __tablename__ = "currency_products"
    
    id: Mapped[auto_int_pk]
    
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="商品名称")
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="商品描述")
    
    price: Mapped[int] = mapped_column(nullable=False, comment="价格(代币)")
    
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="分类")
    
    action_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="行为类型")
    
    reward_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="实际效果参数")
    
    stock: Mapped[int] = mapped_column(Integer, default=-1, server_default=text("-1"), comment="库存")
    
    visible_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="可见条件")
    
    purchase_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="购买条件")
    
    start_time: Mapped[dt | None] = mapped_column(DateTime, nullable=True, comment="上架时间")
    
    end_time: Mapped[dt | None] = mapped_column(DateTime, nullable=True, comment="下架时间")
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"), comment="是否上架")
    
    __table_args__ = (
        Index("idx_currency_products_cat_active", "category", "is_active"),
    )
