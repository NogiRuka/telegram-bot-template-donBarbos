"""
数据库模型基类模块

本模块定义了所有数据库模型的基类和通用字段类型，
提供了统一的字段定义和基础功能。

作者: Telegram Bot Template
创建时间: 2024-01-23
最后更新: 2025-10-21
"""

from __future__ import annotations
import datetime
from typing import Annotated

from sqlalchemy import BigInteger, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bot.utils.datetime import now

# ==================== 通用字段类型定义 ====================

# 主键字段类型
int_pk = Annotated[int, mapped_column(primary_key=True, unique=True, autoincrement=False, comment="整型主键，不自增")]

# 大整型主键字段类型（适用于Telegram ID等大数值）
big_int_pk = Annotated[
    int,
    mapped_column(
        primary_key=True,
        unique=True,
        autoincrement=False,
        type_=BigInteger,
        comment="大整型主键，适用于Telegram ID等大数值，不自增",
    ),
]

# 自增主键字段类型
auto_int_pk = Annotated[int, mapped_column(primary_key=True, autoincrement=True, comment="自增整型主键")]

# 创建时间字段类型
created_at = Annotated[
    datetime.datetime,
    mapped_column(default=now, nullable=False, comment="记录创建时间，自动设置为当前时间"),
]

# 更新时间字段类型
updated_at = Annotated[
    datetime.datetime,
    mapped_column(
        default=now,
        onupdate=now,
        nullable=False,
        comment="记录更新时间，创建时设置为当前时间，更新时自动更新",
    ),
]

# 软删除字段类型
deleted_at = Annotated[
    datetime.datetime | None,
    mapped_column(nullable=True, default=None, comment="软删除时间，NULL表示未删除，有值表示删除时间"),
]

# 软删除标志字段类型
is_deleted = Annotated[
    bool,
    mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="软删除标志，False表示未删除，True表示已删除"
    ),
]

# 创建者ID字段类型
created_by = Annotated[
    int | None, mapped_column(BigInteger, nullable=True, index=True, comment="创建者用户ID，NULL表示系统创建")
]

# 更新者ID字段类型
updated_by = Annotated[
    int | None, mapped_column(BigInteger, nullable=True, index=True, comment="最后更新者用户ID，NULL表示系统更新")
]

# 删除者ID字段类型
deleted_by = Annotated[
    int | None, mapped_column(BigInteger, nullable=True, index=True, comment="删除者用户ID，NULL表示系统删除")
]

# 版本号字段类型（用于乐观锁）
version = Annotated[int, mapped_column(default=1, nullable=False, comment="记录版本号，用于乐观锁控制并发更新")]

# 备注字段类型（TEXT）
remark = Annotated[str | None, mapped_column(Text, nullable=True, comment="备注（长文本）")]


# ==================== 基类定义 ====================


class Base(DeclarativeBase):
    """
    所有数据库模型的基类

    提供了统一的字符串表示方法和基础配置。
    所有模型都应该继承此类。

    属性:
        repr_cols_num: 在__repr__中显示的前N个列数，默认为3
        repr_cols: 额外要在__repr__中显示的列名元组
    """

    # 在__repr__中显示的前N个列数
    repr_cols_num: int = 3

    # 额外要在__repr__中显示的列名
    repr_cols: tuple[str, ...] = ()

    def __repr__(self) -> str:
        """
        返回模型的字符串表示

        显示模型类名和指定的列值，用于调试和日志记录。

        返回:
            str: 格式化的字符串表示，如 <User id=1, name=张三, created_at=2024-01-01>
        """
        cols = [
            f"{col}={getattr(self, col)}"
            for idx, col in enumerate(self.__table__.columns.keys())
            if col in self.repr_cols or idx < self.repr_cols_num
        ]
        return f"<{self.__class__.__name__} {', '.join(cols)}>"


class TimestampMixin:
    """
    时间戳混入类

    为模型提供创建时间和更新时间字段。
    适用于需要记录时间戳的模型。

    字段:
        created_at: 创建时间，自动设置
        updated_at: 更新时间，自动维护
    """

    # 创建时间
    created_at: Mapped[created_at]

    # 更新时间
    updated_at: Mapped[updated_at]


class OperatorMixin:
    """
    操作者混入类

    为模型提供创建者和更新者字段，用于记录操作人员信息。

    字段:
        created_by: 创建者用户ID
        updated_by: 更新者用户ID
    """

    # 创建者用户ID
    created_by: Mapped[created_by]

    # 更新者用户ID
    updated_by: Mapped[updated_by]


class SoftDeleteMixin:
    """
    软删除混入类

    为模型提供软删除功能，删除时不会真正从数据库中移除记录，
    而是标记为已删除状态。

    字段:
        is_deleted: 删除标志
        deleted_at: 删除时间
        deleted_by: 执行删除操作的用户ID
    """

    # 软删除标志
    is_deleted: Mapped[is_deleted]

    # 删除时间
    deleted_at: Mapped[deleted_at]

    # 执行删除操作的用户ID
    deleted_by: Mapped[deleted_by]


class VersionMixin:
    """
    版本控制混入类

    为模型提供版本号字段，用于实现乐观锁，
    防止并发更新时的数据冲突。

    字段:
        version: 版本号，每次更新时递增
    """

    # 版本号
    version: Mapped[version]


class RemarkMixin:
    """
    备注混入类

    为模型提供备注字段，用于存储额外的说明信息。

    字段:
        remark: 备注信息
    """

    # 备注信息
    remark: Mapped[remark]


class FullAuditMixin(TimestampMixin, OperatorMixin, SoftDeleteMixin, VersionMixin, RemarkMixin):
    """
    完整审计混入类

    组合了时间戳、操作者、软删除、版本控制和备注功能，
    适用于需要完整审计功能的重要业务模型。

    包含字段:
        - 时间戳: created_at, updated_at
        - 操作者: created_by, updated_by
        - 软删除: is_deleted, deleted_at, deleted_by
        - 版本控制: version
        - 备注: remark
    """


class BasicAuditMixin(TimestampMixin, OperatorMixin, SoftDeleteMixin, RemarkMixin):
    """
    基础审计混入类

    组合了时间戳、操作者和软删除功能，
    适用于大多数需要基础审计功能的模型。

    包含字段:
        - 时间戳: created_at, updated_at
        - 操作者: created_by, updated_by
        - 软删除: is_deleted, deleted_at, deleted_by
        - 备注: remark
    """
