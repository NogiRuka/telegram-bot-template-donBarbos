from __future__ import annotations
from typing import TYPE_CHECKING

from aiogram import types
from aiogram.types import FSInputFile
from loguru import logger

from bot.utils.images import get_common_image
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

    async def remember(self, msg: types.Message, user_id: int | None = None) -> None:
        """记录当前消息为主消息

        功能说明:
        - 将传入的消息作为用户的主消息保存, 便于后续按ID更新
        - 私聊中使用 chat.id 作为用户标识（私聊 chat.id 等于用户 ID）

        输入参数:
        - msg: Telegram 消息对象
        - user_id: 用户ID, 可选; 若不传则使用 chat.id

        返回值:
        - None
        """
        with logger.catch():
            uid = user_id or msg.chat.id
            self._messages[uid] = (msg.chat.id, msg.message_id)
            logger.debug(f"🔍 remember: uid={uid}, chat_id={msg.chat.id}, message_id={msg.message_id}")

    async def update(
        self,
        user_id: int,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str | None = None,
    ) -> bool:
        """更新主消息内容
        
        功能说明:
        - 根据已记录的 `(chat_id, message_id)` 编辑主消息的 caption/文本与键盘
        
        输入参数:
        - user_id: Telegram 用户ID
        - caption: 文本说明内容
        - kb: 内联键盘
        - image_path: 图片路径，可选。如果提供，可能需要重新发送消息以带上图片
        
        返回值:
        - bool: 是否更新成功
        """
        ids = self.get_main_msg(user_id)
        logger.debug(f"🔍 update: user_id={user_id}, ids={ids}, _messages={self._messages}")
        if not ids:
            logger.warning(f"⚠️ update: 未找到用户 {user_id} 的主消息")
            # 尝试作为新消息发送（兜底逻辑）
            if image_path:
                try:
                    file = FSInputFile(image_path)
                    msg = await self.bot.send_photo(chat_id=user_id, photo=file, caption=caption, reply_markup=kb)
                    self._messages[user_id] = (msg.chat.id, msg.message_id)
                    return True
                except Exception as e:
                    logger.error(f"❌ update: 发送兜底图片消息失败: {e}")
            else:
                try:
                    msg = await self.bot.send_message(chat_id=user_id, text=caption, reply_markup=kb)
                    self._messages[user_id] = (msg.chat.id, msg.message_id)
                    return True
                except Exception as e:
                    logger.error(f"❌ update: 发送兜底文本消息失败: {e}")
            return False

        chat_id, message_id = ids
        
        # 如果需要更新图片，目前 edit_message_content_by_id 仅支持修改文本/caption
        # 若要修改图片本身或从纯文本转为图片，通常需要删除旧消息发新消息，或者使用 editMessageMedia
        # 这里为了简化，如果提供了 image_path 且当前可能不是图片消息，或者需要刷新图片
        # 我们可以尝试使用 edit_message_media，或者简单地删除重发。
        # 鉴于 MainMessageService 的设计，edit_message_content_by_id 主要处理 caption/kb
        # 如果传入了 image_path，我们尝试调用 render_view 逻辑的变体，或者直接 delete & send
        
        if image_path:
            # 简单粗暴：删除旧消息，发送新消息（确保图片显示）
            # 缺点：界面会闪烁。优点：确保图片和类型正确。
            try:
                await self.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            
            try:
                file = FSInputFile(image_path)
                msg = await self.bot.send_photo(chat_id=chat_id, photo=file, caption=caption, reply_markup=kb)
                self._messages[user_id] = (msg.chat.id, msg.message_id)
                return True
            except Exception as e:
                logger.error(f"❌ update: 重发带图片消息失败: {e}")
                return False

        with logger.catch():
            result = await edit_message_content_by_id(self.bot, chat_id, message_id, caption, kb)
            logger.debug(f"🔍 update: edit result={result}")
            return result
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

        image_path = get_common_image()
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

