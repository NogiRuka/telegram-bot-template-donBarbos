from __future__ import annotations
from typing import TYPE_CHECKING

from aiogram import types
from aiogram.types import FSInputFile
from loguru import logger

from bot.utils.view import edit_message_content_by_id, render_view

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

        输入参数:
        - bot: Telegram Bot 实例

        返回值:
        - None
        """
        self.bot = bot
        self._messages: dict[int, tuple[int, int]] = {}

    async def send_main(
        self,
        message: types.Message,
        photo: str | None,
        caption: str,
        kb: types.InlineKeyboardMarkup,
    ) -> None:
        """首次发送主消息

        功能说明:
        - 在私聊中发送一条主消息(图片+caption+键盘或纯文本), 并记录该消息ID

        输入参数:
        - message: 用户触发 `/start` 的消息对象
        - photo: 图片路径, 传入空字符串或 None 表示发送纯文本
        - caption: 主消息的说明文本
        - kb: 主消息的内联键盘

        返回值:
        - None
        """
        with logger.catch():
            if photo:
                file = FSInputFile(photo)
                msg = await message.answer_photo(
                    photo=file, caption=caption, reply_markup=kb, parse_mode="MarkdownV2"
                )
            else:
                msg = await message.answer(caption, reply_markup=kb, parse_mode="MarkdownV2")
            if message.from_user:
                self._messages[message.from_user.id] = (msg.chat.id, msg.message_id)

    def get_main_msg(self, user_id: int) -> tuple[int, int] | None:
        """获取主消息标识

        功能说明:
        - 返回指定用户的主消息 `(chat_id, message_id)`, 若不存在返回 None

        输入参数:
        - user_id: Telegram 用户ID

        返回值:
        - tuple[int, int] | None: 主消息标识或 None
        """
        return self._messages.get(user_id)

    async def remember(self, msg: types.Message) -> None:
        """记录当前消息为主消息

        功能说明:
        - 将传入的消息作为用户的主消息保存, 便于后续按ID更新

        输入参数:
        - msg: Telegram 消息对象

        返回值:
        - None
        """
        with logger.catch():
            if msg.from_user:
                self._messages[msg.from_user.id] = (msg.chat.id, msg.message_id)

    async def update(self, user_id: int, caption: str, kb: types.InlineKeyboardMarkup) -> bool:
        """更新主消息内容

        功能说明:
        - 根据已记录的 `(chat_id, message_id)` 编辑主消息的 caption/文本与键盘

        输入参数:
        - user_id: Telegram 用户ID
        - caption: 文本说明内容
        - kb: 内联键盘

        返回值:
        - bool: 是否更新成功
        """
        ids = self.get_main_msg(user_id)
        if not ids:
            return False
        chat_id, message_id = ids
        with logger.catch():
            return await edit_message_content_by_id(self.bot, chat_id, message_id, caption, kb)
        return False

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

    async def update_by_message(
        self,
        msg: types.Message,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str | None = None,
    ) -> bool:
        """按消息对象更新主消息

        功能说明:
        - 直接编辑传入的消息对象, 优先保持媒体不变, 仅编辑 caption 与键盘; 如有 `image_path` 则尝试替换为图片

        输入参数:
        - msg: Telegram 消息对象
        - caption: 文本说明内容
        - kb: 内联键盘
        - image_path: 图片路径, 可选

        返回值:
        - bool: 是否更新成功
        """
        with logger.catch():
            ok = await render_view(msg, image_path or "", caption, kb)
            await self.remember(msg)
            return ok
        return False

    async def update_on_callback(
        self,
        callback: types.CallbackQuery,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str | None = None,
    ) -> bool:
        """按回调查询更新主消息

        功能说明:
        - 优先编辑 `callback.message` 这条可见消息, 并记录为主消息; 如不可编辑则回退按用户ID更新

        输入参数:
        - callback: 回调对象
        - caption: 文本说明内容
        - kb: 内联键盘
        - image_path: 图片路径, 可选

        返回值:
        - bool: 是否更新成功
        """
        msg = callback.message if isinstance(callback.message, types.Message) else None
        uid = callback.from_user.id if callback.from_user else None
        if msg is not None:
            is_media = bool(
                getattr(msg, "photo", None)
                or getattr(msg, "video", None)
                or getattr(msg, "animation", None)
                or getattr(msg, "document", None)
            )
            # 若希望展示图片而当前消息不是媒体消息, 直接新发图片并删除旧消息
            if image_path and not is_media:
                with logger.catch():
                    file = FSInputFile(image_path)
                    new_msg = await msg.answer_photo(file, caption=caption, reply_markup=kb)
                    await msg.delete()
                    await self.remember(new_msg)
                    return True

            ok = await self.update_by_message(msg, caption, kb, image_path)
            if ok:
                return True
            # 失败时回退为新发图片消息并删除旧消息
            if image_path:
                with logger.catch():
                    file = FSInputFile(image_path)
                    new_msg = await msg.answer_photo(file, caption=caption, reply_markup=kb)
                    await msg.delete()
                    await self.remember(new_msg)
                    return True
            return False
        if uid is not None:
            return await self.update(uid, caption, kb)
        return False

