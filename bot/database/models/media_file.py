from __future__ import annotations

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class MediaFileModel(Base, BasicAuditMixin):
    """通用媒体文件模型

    功能说明:
    - 存储用户上传的文件/图片/视频/音频等通用媒体信息
    - 统一用于管理员文件管理的保存与查看

    输入参数:
    - 无

    返回值:
    - 无
    """
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="自增主键")

    # Telegram 基本文件信息
    file_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="文件ID")
    file_unique_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True, comment="文件唯一ID")
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="文件大小(字节)")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件名")
    unique_name: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, comment="唯一文件名(文件名_时间戳)")
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="MIME类型")

    # 类型与可选属性
    media_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="媒体类型(photo, document, video, audio, voice, animation, sticker, etc)")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="宽度(图片/视频)")
    height: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="高度(图片/视频)")
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="时长(音频/视频, 秒)")

    # 备注与标签
    label: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="标签/备注")
    extra: Mapped[str | None] = mapped_column(Text, nullable=True, comment="扩展信息(JSON 字符串)")

    __table_args__ = (
        Index("idx_media_files_type", "media_type"),
        Index("idx_media_files_file_id", "file_id"),
    )

