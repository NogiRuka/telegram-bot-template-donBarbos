from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


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
