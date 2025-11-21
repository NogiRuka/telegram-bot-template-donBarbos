"""
消息导出服务模块

本模块提供群组消息的查询、过滤和导出功能，
支持多种导出格式（TXT、CSV、JSON）。

作者: Telegram Bot Template
创建时间: 2025-01-21
最后更新: 2025-01-21
"""

import csv
import json
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from typing import Any

from loguru import logger
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import MessageModel, MessageType


class MessageExportService:
    """消息导出服务类"""

    def __init__(self, session: AsyncSession) -> None:
        """
        初始化消息导出服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_messages(
        self,
        chat_id: int,
        limit: int = 1000,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        message_types: list[MessageType] | None = None,
        search_text: str | None = None,
        user_id: int | None = None,
        include_forwarded: bool = True,
        include_replies: bool = True,
        include_bot_messages: bool = True
    ) -> tuple[list[MessageModel], int]:
        """
        查询群组消息

        Args:
            chat_id: 群组聊天ID
            limit: 限制数量
            offset: 偏移量
            start_date: 开始日期
            end_date: 结束日期
            message_types: 消息类型列表
            search_text: 搜索文本
            user_id: 用户ID
            include_forwarded: 是否包含转发消息
            include_replies: 是否包含回复消息
            include_bot_messages: 是否包含机器人消息

        Returns:
            Tuple[List[MessageModel], int]: 消息列表和总数
        """
        try:
            # 构建查询条件
            conditions = [MessageModel.chat_id == chat_id]

            # 日期范围过滤
            if start_date:
                conditions.append(MessageModel.created_at >= start_date)
            if end_date:
                conditions.append(MessageModel.created_at <= end_date)

            # 消息类型过滤
            if message_types:
                conditions.append(MessageModel.message_type.in_(message_types))

            # 文本搜索
            if search_text:
                search_conditions = []
                if MessageModel.text:
                    search_conditions.append(MessageModel.text.ilike(f"%{search_text}%"))
                if MessageModel.caption:
                    search_conditions.append(MessageModel.caption.ilike(f"%{search_text}%"))
                if search_conditions:
                    conditions.append(or_(*search_conditions))

            # 用户过滤
            if user_id:
                conditions.append(MessageModel.user_id == user_id)

            # 转发消息过滤
            if not include_forwarded:
                conditions.append(not MessageModel.is_forwarded)

            # 回复消息过滤
            if not include_replies:
                conditions.append(MessageModel.reply_to_message_id.is_(None))

            # 机器人消息过滤
            if not include_bot_messages:
                conditions.append(not MessageModel.is_bot)

            # 查询总数
            count_query = func.count(MessageModel.id).filter(and_(*conditions))
            total_count = await self.session.scalar(count_query)

            # 查询消息
            query = (
                self.session.query(MessageModel)
                .filter(and_(*conditions))
                .order_by(desc(MessageModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(query)
            messages = result.scalars().all()

            return list(messages), total_count or 0

        except Exception as e:
            logger.error(f"查询消息失败: {e}")
            return [], 0

    async def export_to_txt(
        self,
        chat_id: int,
        **kwargs
    ) -> BytesIO:
        """
        导出消息为TXT格式

        Args:
            chat_id: 群组聊天ID
            **kwargs: 查询参数

        Returns:
            BytesIO: TXT文件内容
        """
        try:
            messages, _ = await self.get_messages(chat_id, **kwargs)

            output = StringIO()
            output.write(f"群组消息导出 - Chat ID: {chat_id}\n")
            output.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output.write(f"消息总数: {len(messages)}\n")
            output.write("=" * 50 + "\n\n")

            for message in messages:
                # 消息头部信息
                output.write(f"消息ID: {message.message_id}\n")
                output.write(f"用户ID: {message.user_id}\n")
                output.write(f"时间: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                output.write(f"类型: {message.message_type.value}\n")

                # 消息内容
                if message.text:
                    output.write(f"内容: {message.text}\n")
                elif message.caption:
                    output.write(f"说明: {message.caption}\n")

                # 文件信息
                if message.file_id:
                    output.write(f"文件ID: {message.file_id}\n")
                    if message.file_name:
                        output.write(f"文件名: {message.file_name}\n")
                    if message.file_size:
                        output.write(f"文件大小: {message.file_size} bytes\n")

                # 特殊标记
                if message.is_forwarded:
                    output.write("标记: 转发消息\n")
                if message.reply_to_message_id:
                    output.write(f"回复消息ID: {message.reply_to_message_id}\n")
                if message.is_edited:
                    output.write("标记: 已编辑\n")

                output.write("-" * 30 + "\n\n")

            # 转换为BytesIO
            content = output.getvalue()
            output.close()

            bytes_output = BytesIO()
            bytes_output.write(content.encode("utf-8"))
            bytes_output.seek(0)

            return bytes_output

        except Exception as e:
            logger.error(f"导出TXT失败: {e}")
            raise

    async def export_to_csv(
        self,
        chat_id: int,
        **kwargs
    ) -> BytesIO:
        """
        导出消息为CSV格式

        Args:
            chat_id: 群组聊天ID
            **kwargs: 查询参数

        Returns:
            BytesIO: CSV文件内容
        """
        try:
            messages, _ = await self.get_messages(chat_id, **kwargs)

            output = StringIO()
            writer = csv.writer(output)

            # 写入表头
            headers = [
                "消息ID", "用户ID", "聊天ID", "消息类型", "文本内容",
                "媒体说明", "文件ID", "文件名", "文件大小", "是否转发",
                "回复消息ID", "是否编辑", "字符数", "单词数", "语言代码",
                "情感分数", "创建时间", "更新时间"
            ]
            writer.writerow(headers)

            # 写入数据
            for message in messages:
                row = [
                    message.message_id,
                    message.user_id,
                    message.chat_id,
                    message.message_type.value,
                    message.text or "",
                    message.caption or "",
                    message.file_id or "",
                    message.file_name or "",
                    message.file_size or "",
                    "是" if message.is_forwarded else "否",
                    message.reply_to_message_id or "",
                    "是" if message.is_edited else "否",
                    message.char_count or 0,
                    message.word_count or 0,
                    message.language_code or "",
                    message.sentiment_score or 0.0,
                    message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    message.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                ]
                writer.writerow(row)

            # 转换为BytesIO
            content = output.getvalue()
            output.close()

            bytes_output = BytesIO()
            bytes_output.write(content.encode("utf-8-sig"))  # 使用BOM以支持Excel
            bytes_output.seek(0)

            return bytes_output

        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            raise

    async def export_to_json(
        self,
        chat_id: int,
        **kwargs
    ) -> BytesIO:
        """
        导出消息为JSON格式

        Args:
            chat_id: 群组聊天ID
            **kwargs: 查询参数

        Returns:
            BytesIO: JSON文件内容
        """
        try:
            messages, total_count = await self.get_messages(chat_id, **kwargs)

            # 构建导出数据
            export_data = {
                "export_info": {
                    "chat_id": chat_id,
                    "export_time": datetime.now().isoformat(),
                    "total_messages": total_count,
                    "exported_messages": len(messages)
                },
                "messages": []
            }

            for message in messages:
                message_data = {
                    "message_id": message.message_id,
                    "user_id": message.user_id,
                    "chat_id": message.chat_id,
                    "message_type": message.message_type.value,
                    "text": message.text,
                    "caption": message.caption,
                    "file_info": {
                        "file_id": message.file_id,
                        "file_name": message.file_name,
                        "file_size": message.file_size,
                        "mime_type": message.mime_type
                    } if message.file_id else None,
                    "flags": {
                        "is_forwarded": message.is_forwarded,
                        "is_edited": message.is_edited,
                        "is_bot": message.is_bot
                    },
                    "reply_to_message_id": message.reply_to_message_id,
                    "statistics": {
                        "char_count": message.char_count,
                        "word_count": message.word_count,
                        "language_code": message.language_code,
                        "sentiment_score": message.sentiment_score
                    },
                    "timestamps": {
                        "created_at": message.created_at.isoformat(),
                        "updated_at": message.updated_at.isoformat()
                    }
                }
                export_data["messages"].append(message_data)

            # 转换为JSON字符串
            json_content = json.dumps(export_data, ensure_ascii=False, indent=2)

            # 转换为BytesIO
            bytes_output = BytesIO()
            bytes_output.write(json_content.encode("utf-8"))
            bytes_output.seek(0)

            return bytes_output

        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            raise

    async def get_message_statistics(
        self,
        chat_id: int,
        days: int = 30
    ) -> dict[str, Any]:
        """
        获取消息统计信息

        Args:
            chat_id: 群组聊天ID
            days: 统计天数

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            start_date = datetime.now() - timedelta(days=days)

            # 总消息数
            total_query = (
                func.count(MessageModel.id)
                .filter(
                    and_(
                        MessageModel.chat_id == chat_id,
                        MessageModel.created_at >= start_date
                    )
                )
            )
            total_messages = await self.session.scalar(total_query) or 0

            # 按类型统计
            type_query = (
                self.session.query(
                    MessageModel.message_type,
                    func.count(MessageModel.id).label("count")
                )
                .filter(
                    and_(
                        MessageModel.chat_id == chat_id,
                        MessageModel.created_at >= start_date
                    )
                )
                .group_by(MessageModel.message_type)
            )

            type_result = await self.session.execute(type_query)
            type_stats = {row.message_type.value: row.count for row in type_result}

            # 活跃用户统计
            user_query = (
                self.session.query(
                    MessageModel.user_id,
                    func.count(MessageModel.id).label("count")
                )
                .filter(
                    and_(
                        MessageModel.chat_id == chat_id,
                        MessageModel.created_at >= start_date
                    )
                )
                .group_by(MessageModel.user_id)
                .order_by(desc("count"))
                .limit(10)
            )

            user_result = await self.session.execute(user_query)
            top_users = [
                {"user_id": row.user_id, "message_count": row.count}
                for row in user_result
            ]

            # 按日期统计
            daily_query = (
                self.session.query(
                    func.date(MessageModel.created_at).label("date"),
                    func.count(MessageModel.id).label("count")
                )
                .filter(
                    and_(
                        MessageModel.chat_id == chat_id,
                        MessageModel.created_at >= start_date
                    )
                )
                .group_by(func.date(MessageModel.created_at))
                .order_by("date")
            )

            daily_result = await self.session.execute(daily_query)
            daily_stats = [
                {"date": row.date.isoformat(), "count": row.count}
                for row in daily_result
            ]

            return {
                "chat_id": chat_id,
                "period_days": days,
                "total_messages": total_messages,
                "message_types": type_stats,
                "top_users": top_users,
                "daily_statistics": daily_stats,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取消息统计失败: {e}")
            return {}


# 导出服务类
__all__ = ["MessageExportService"]
