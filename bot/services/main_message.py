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

    def get(self, user_id: int) -> tuple[int, int] | None:
        """获取已记录的主消息"""
        logger.debug(f"🔍 self._messages: {self._messages}, user_id={user_id}")
        return self._messages.get(user_id)

    # async def remember(self, msg: types.Message, user_id: int | None = None) -> None:
    #     """记录当前消息为主消息"""
    #     with logger.catch():
    #         uid = user_id or msg.chat.id
    #         self._messages[uid] = (msg.chat.id, msg.message_id)
    #         logger.debug(f"🔍 remember: uid={uid}, chat_id={msg.chat.id}, message_id={msg.message_id}")

    def remember(self, user_id: int, msg: types.Message) -> None:
        """记录主消息"""
        logger.debug(f"🔍 remember: user_id={user_id}, chat_id={msg.chat.id}, message_id={msg.message_id}")
        self._messages[user_id] = (msg.chat.id, msg.message_id)

    async def _send_new(
        self,
        user_id: int,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str,
    ) -> bool:
        """发送新的图片主消息并记录"""
        try:
            file = FSInputFile(image_path)
            msg = await self.bot.send_photo(
                chat_id=user_id,
                photo=file,
                caption=caption,
                reply_markup=kb,
                parse_mode="MarkdownV2",
            )
            self.remember(user_id, msg)
            return True
        except Exception as e:
            # 这里不抛异常，统一由调用方根据 False 判断
            print(f"❌ 主消息发送失败: {e}")
            return False

    async def render(
        self,
        user_id: int,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str | None = None,
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
            if not image_path:
                # 业务错误：首次渲染却没有图片
                print("❌ 尚未存在主消息，必须提供 image_path")
                return False

            return await self._send_new(user_id, caption, kb, image_path)

        chat_id, message_id = ids

        # ② 不更换图片，仅更新 caption
        if image_path is None:
            try:
                await self.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="MarkdownV2",
                )
                return True
            except Exception as e:
                # caption 未变化时，Telegram 会抛 message is not modified
                if "message is not modified" in str(e):
                    return True

                print(f"⚠️ 更新 caption 失败: {e}")
                return False

        # ③ 明确更换图片：删除旧消息并重发
        try:
            await self.bot.delete_message(chat_id, message_id)
        except Exception:
            pass

        return await self._send_new(user_id, caption, kb, image_path)



    async def update(
        self,
        user_id: int,
        caption: str,
        kb: types.InlineKeyboardMarkup,
        image_path: str | None = None,
    ) -> bool:
        """
        主消息固定为：photo + caption (兼容文本)
        """
        ids = self.get_main_msg(user_id)
        logger.debug(f"🔍 update: user_id={user_id}, ids={ids}")

        async def _send_new():
            try:
                if image_path:
                    file = FSInputFile(image_path)
                    msg = await self.bot.send_photo(
                        chat_id=user_id,
                        photo=file,
                        caption=caption,
                        reply_markup=kb,
                        parse_mode="MarkdownV2",
                    )
                else:
                    msg = await self.bot.send_message(
                        chat_id=user_id,
                        text=caption,
                        reply_markup=kb,
                        parse_mode="MarkdownV2",
                    )
                self._messages[user_id] = (msg.chat.id, msg.message_id)
                return True
            except Exception as e:
                logger.error(f"❌ update: 发送主消息失败: {e}")
                return False

        # ① 没有主消息 → 直接发
        if not ids:
            logger.warning("⚠️ update: 未找到主消息，直接发送")
            return await _send_new()

        chat_id, message_id = ids

        # ② 优先 edit caption
        try:
            logger.debug("🔍 update: edit_message_caption")
            await self.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="MarkdownV2",
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️ update: edit 失败，重发主消息: {e}")

        # ③ edit 失败 → 删除旧的
        try:
            await self.bot.delete_message(chat_id, message_id)
        except Exception:
            pass

        # ④ 重发
        return await _send_new()



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
            ok = await render_view(msg, caption, kb, image_path=image_path)
            if msg.from_user:
                self.remember(msg.from_user.id, msg)
            return ok

    async def update_on_callback(
        self,
        callback: types.CallbackQuery,
        caption: str,
        kb: types.InlineKeyboardMarkup,
    ) -> bool:
        """
        回调场景下刷新主消息

        设计约定：
        - 主消息统一由 render 管理
        - callback.message 不再单独处理
        """
        uid = callback.from_user.id if callback.from_user else None
        if not uid:
            return False

        return await self.render(uid, caption, kb, image_path=None)