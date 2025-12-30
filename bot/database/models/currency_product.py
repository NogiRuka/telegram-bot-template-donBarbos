from datetime import datetime as dt
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


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
    - stock: 库存 (-1表示无限)
    - visible_conditions: 可见条件 (JSON)
    - purchase_conditions: 购买条件 (JSON)
    - start_time: 上架时间
    - end_time: 下架时间
    - is_active: 是否上架
    """

    __tablename__ = "currency_products"

    id: Mapped[auto_int_pk]

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="商品名称")

    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="商品描述")

    price: Mapped[int] = mapped_column(nullable=False, comment="价格(代币)")

    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="分类")

    action_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="行为类型")

    stock: Mapped[int] = mapped_column(Integer, default=-1, server_default=text("-1"), comment="库存")

    visible_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="可见条件")

    purchase_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="购买条件")

    start_time: Mapped[dt | None] = mapped_column(DateTime, nullable=True, comment="上架时间")

    end_time: Mapped[dt | None] = mapped_column(DateTime, nullable=True, comment="下架时间")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"), comment="是否上架")

    __table_args__ = (
        Index("idx_currency_products_cat_active", "category", "is_active"),
    )
