from __future__ import annotations
import contextlib
from typing import TYPE_CHECKING

from aiogram import types
from aiogram.types import FSInputFile
from loguru import logger

if TYPE_CHECKING:
    from aiogram import Bot


class MainMessageService:
    """主消息管理服务

    功能说明:
    - 统一管理每个用户的主消息(图片+caption+键盘), 保存其 `chat_id` 与 `message_id`
    - 提供首次发送、更新主消息内容、删除用户输入消息、记录主消息等能力
    - 异步调用方式: 使用 `await` 调用本类的异步方法

    依赖安装:
    - aiogram: `pip install aiogram`
    - loguru: `pip install loguru`

    Telegram API 限制:
    - caption/文本最长约 4096 字符
    - 频繁编辑可能触发限流, 请合理控制频率
    """

    def __init__(self, bot: Bot) -> None:
        """构造函数
        功能说明:
        - 初始化服务, 持有 `Bot` 实例并创建内存映射表
        """
        self.bot = bot
        self._messages: dict[int, tuple[int, int]] = {}

    def get(self, user_id: int) -> tuple[int, int] | None:
        """获取已记录的主消息"""
        # logger.debug(f"🔍 self._messages: {self._messages}, user_id={user_id}")
        return self._messages.get(user_id)

    def reset(self, user_id: int) -> None:
        """清除用户当前主消息记录"""
        if user_id in self._messages:
            self._messages.pop(user_id)

    def remember(self, user_id: int, msg: types.Message) -> None:
        """记录主消息"""
        # logger.debug(f"🔍 remember: user_id={user_id}, chat_id={msg.chat.id}, message_id={msg.message_id}")
        self._messages[user_id] = (msg.chat.id, msg.message_id)

    async def _send_new(
        self,
        user_id: int,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str | None = None,
        image_file_id: str | None = None,
        image_source_type: str | None = None,
        parse_mode: str | None = "MarkdownV2",
    ) -> bool:
        """发送新的图片主消息并记录"""
        try:
            if image_file_id:
                # 始终使用 send_photo 保持主消息样式一致
                msg = await self.bot.send_photo(
                    chat_id=user_id,
                    photo=image_file_id,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode=parse_mode,
                )
            else:
                file = FSInputFile(image_path or "")
                msg = await self.bot.send_photo(
                    chat_id=user_id,
                    photo=file,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode=parse_mode,
                )
            self.remember(user_id, msg)
            return True
        except Exception:
            # 这里不抛异常，统一由调用方根据 False 判断
            return False

    async def render(
        self,
        user_id: int,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str | None = None,
        image_file_id: str | None = None,
        image_source_type: str | None = None,
        parse_mode: str | None = "MarkdownV2",
    ) -> bool:
        """
        渲染主消息（唯一对外入口）

        行为规则：
        - 尚无主消息 → 必须提供 image_path，发送新图片消息
        - image_path 为 None → 仅更新 caption
        - image_path 不为 None → 更换图片（删除旧消息并重发）
        """
        ids = self.get(user_id)

        # ① 尚未有主消息
        if not ids:
            if not image_path and not image_file_id:
                # 业务错误：首次渲染却没有图片
                return False

            return await self._send_new(
                user_id,
                caption,
                kb,
                image_path=image_path,
                image_file_id=image_file_id,
                image_source_type=image_source_type,
                parse_mode=parse_mode,
            )

        chat_id, message_id = ids

        # ② 不更换图片，仅更新 caption
        if image_path is None and image_file_id is None:
            try:
                await self.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode=parse_mode,
                )
                return True
            except Exception as e:
                logger.error(f"更新 caption 失败: {e}")
                return False

        # ③ 明确更换图片：删除旧消息并重发
        with contextlib.suppress(Exception):
            await self.bot.delete_message(chat_id, message_id)

        return await self._send_new(
            user_id,
            caption,
            kb,
            image_path=image_path,
            image_file_id=image_file_id,
            image_source_type=image_source_type,
            parse_mode=parse_mode,
        )


    async def delete_input(self, input_message: types.Message) -> None:
        """删除用户输入消息

        功能说明:
        - 删除用户刚刚发送的输入消息, 保持对话整洁

        输入参数:
        - input_message: 用户输入的消息对象

        返回值:
        - None
        """
        with logger.catch():
            await input_message.delete()

    async def update_on_callback(
        self,
        callback: types.CallbackQuery,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        parse_mode: str | None = "MarkdownV2",
    ) -> bool:
        """
        回调场景下刷新主消息

        设计说明：
        - 如果内存中没有主消息，但 callback.message 存在
        则将该消息重新记录为主消息
        - 然后统一交由 render 处理
        """
        uid = callback.from_user.id if callback.from_user else None
        msg = callback.message if isinstance(callback.message, types.Message) else None

        if not uid:
            return False

        # ⭐ 关键修复点：内存丢失，但用户点了旧主消息
        self.remember(uid, msg)

        return await self.render(uid, caption, kb, parse_mode=parse_mode)
