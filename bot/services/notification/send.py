from __future__ import annotations
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError
from aiohttp import ClientError
from loguru import logger

from bot.services.notification.action import NotificationActionService
from bot.services.notification.query import NotificationQueryService
from bot.utils.notification import get_notification_content

if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import AsyncSession


async def _send_to_chat(bot: Bot, chat_id: str | int, msg_text: str, image_url: str | None) -> bool:
    """发送单条通知到指定 chat_id。

    功能说明:
    - 封装 Telegram API 发送, 统一异常处理
    - 成功返回 True, 失败返回 False

    输入参数:
    - bot: Aiogram Bot 实例
    - chat_id: 目标 chat_id 或 @username
    - msg_text: 发送文本(HTML)
    - image_url: 图片URL, None 表示纯文本

    返回值:
    - bool: 是否发送成功
    """

    try:
        if image_url:
            await bot.send_photo(chat_id=chat_id, photo=image_url, caption=msg_text)
        else:
            await bot.send_message(chat_id=chat_id, text=msg_text)
    except (TelegramAPIError, ClientError) as e:
        logger.error(f"❌ 发送通知到 {chat_id} 失败: {e}")
        return False
    else:
        return True


class NotificationSendService:
    @staticmethod
    async def send_all(
        session: AsyncSession,
        bot: Bot,
        target_chat_ids: list[str | int],
        updated_by: int | None = None,
    ) -> tuple[int, int]:
        """发送所有待发送通知(按业务Key去重后发送)。

        功能说明:
        - 以预览查询结果作为发送来源, 确保去重规则与预览一致
        - 对每个业务实体只发送一次
        - 发送后按业务实体更新同组通知状态

        输入参数:
        - session: AsyncSession 数据库会话
        - bot: Aiogram Bot 实例
        - target_chat_ids: 目标频道/群组ID列表
        - updated_by: 操作者用户ID(可选)

        返回值:
        - tuple[int, int]: (成功数量, 失败数量)
        """

        rows = await NotificationQueryService.get_preview_rows(session)
        if not rows:
            return 0, 0

        sent_count = 0
        failed_count = 0

        for _notif, item in rows:
            msg_text, image_url = get_notification_content(item)
            send_success = False

            for chat_id in target_chat_ids:
                send_success = (await _send_to_chat(bot, chat_id, msg_text, image_url)) or send_success

            await NotificationActionService.mark_group_sent(
                session=session,
                biz_id=item.id,
                target_channels=target_chat_ids,
                success=send_success,
                updated_by=updated_by,
            )

            if send_success:
                sent_count += 1
            else:
                failed_count += 1

        await session.commit()
        return sent_count, failed_count
