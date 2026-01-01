"""消息处理工具模块。

这个模块提供与消息相关的通用工具函数，包括消息删除、延迟删除等功能。
适用于整个应用中的消息处理需求。
"""

from __future__ import annotations
import asyncio
from typing import Any

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger


async def safe_delete_message(bot: Any, chat_id: int, message_id: int) -> bool:
    """安全地删除消息，失败时不会抛出异常。

    功能说明:
    - 使用 try-except 捕获所有异常，避免删除失败影响主流程
    - 适用于需要删除消息但不希望删除失败影响主要功能的场景

    输入参数:
    - bot: Bot 实例
    - chat_id: 聊天 ID
    - message_id: 消息 ID

    返回值:
    - bool: 删除是否成功
    """
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception:
        return False


async def delete_message(message: Any) -> bool:
    """安全地删除消息，失败时不会抛出异常。

    功能说明:
    - 使用 try-except 捕获所有异常，避免删除失败影响主流程
    - 适用于需要删除消息但不希望删除失败影响主要功能的场景

    输入参数:
    - message: 要删除的消息对象，需要有 delete() 方法

    返回值:
    - bool: 删除是否成功
    """
    try:
        await message.delete()
        return True
    except Exception:
        return False


def delete_message_after_delay(
    message: Any,
    delay: int = 3,
    chat_id: int | None = None,
    message_id: int | None = None
) -> asyncio.Task:
    """延迟指定时间后删除消息，返回异步任务。

    功能说明:
    - 创建异步任务在指定时间后删除消息
    - 自动保存任务引用避免被垃圾回收
    - 适用于发送临时提示消息后自动清理的场景
    - 支持传入 message 对象或 (bot, chat_id, message_id) 组合

    输入参数:
    - message: 消息对象 (需有 delete 方法) 或 Bot 实例
    - delay: 延迟删除的秒数，默认3秒
    - chat_id: 聊天ID (当 message 为 Bot 实例时必填)
    - message_id: 消息ID (当 message 为 Bot 实例时必填)

    返回值:
    - asyncio.Task: 创建的异步任务
    """
    async def _delayed_delete() -> None:
        try:
            await asyncio.sleep(delay)
            if chat_id and message_id and hasattr(message, "delete_message"):
                # 如果传入的是 Bot 实例和 ID
                await message.delete_message(chat_id=chat_id, message_id=message_id)
            elif hasattr(message, "delete"):
                # 如果传入的是 Message 对象
                await message.delete()
        except Exception as e:
            # 忽略删除过程中的任何错误
            logger.debug(f"延迟删除消息失败: {e}")

    task = asyncio.create_task(_delayed_delete())
    # 保存任务引用避免被垃圾回收
    task._ignore = True
    return task


async def send_temp_message(
    messageable: Message | CallbackQuery,
    text: str,
    delay: int = 10,
    reply_markup: Any = None,
    photo: str | Any = None,
    parse_mode: str = "MarkdownV2"
) -> asyncio.Task | None:
    """发送一条临时消息，并在指定时间后自动删除。
    功能说明:
    - 统一封装发送消息并延迟删除的逻辑
    - 支持 Message 或 CallbackQuery 对象
    - 支持发送图片和键盘
    - 默认使用 MarkdownV2 格式

    输入参数:
    - messageable: Message 或 CallbackQuery 对象，用于发送回复
    - text: 消息内容（若发送图片则作为 caption）
    - delay: 延迟删除秒数，默认10秒
    - reply_markup: 键盘标记（可选）
    - photo: 图片对象或 file_id/url（可选）
    - parse_mode: 消息解析模式，默认 "MarkdownV2"

    返回值:
    - asyncio.Task | None: 删除任务，如果发送失败则返回 None
    """
    try:
        messager = None
        if hasattr(messageable, "message") and messageable.message:
            # 处理回调查询 (CallbackQuery)
            messager = messageable.message
        elif hasattr(messageable, "answer"):
            # 处理普通消息 (Message)
            messager = messageable

        if not messager:
            return None

        if photo:
            sent_msg = await messager.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            sent_msg = await messager.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )

        return delete_message_after_delay(sent_msg, delay)
    except Exception as e:
        logger.error(f"发送临时消息失败: {e}")
        return None

async def send_toast(
    messageable: Message | CallbackQuery,
    text: str,
    delay: int = 3,
    reply_markup: Any = None,
    photo: str | Any = None,
    parse_mode: str | None = None
) -> asyncio.Task | None:
    try:
        # ✅ 明确区分类型，别他妈猜
        if isinstance(messageable, CallbackQuery):
            messager = messageable.message
        elif isinstance(messageable, Message):
            messager = messageable
        else:
            return None

        if not messager:
            return None

        if photo:
            sent_msg = await messager.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            sent_msg = await messager.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )

        # ✅ 延迟删除
        return delete_message_after_delay(sent_msg, delay)
    except Exception as e:
        logger.error(e)


def extract_id(callback_data: str) -> int:
    return int(callback_data.rsplit(":", 1)[-1])


async def clear_message_list_from_state(
    state: FSMContext,
    bot: Bot,
    chat_id: int,
    key: str
) -> None:
    """从状态中获取消息 ID 列表并删除这些消息，然后清空状态中的列表。

    功能说明:
    - 用于批量清理已发送的消息（如列表、菜单等）
    - 从 FSMContext 中读取指定 key 的消息 ID 列表
    - 遍历并安全删除每条消息
    - 最后将状态中的该 key 重置为空列表

    输入参数:
    - state: FSMContext 状态上下文
    - bot: Bot 实例
    - chat_id: 聊天 ID
    - key: 状态中存储消息 ID 列表的键名

    返回值:
    - None
    """
    data = await state.get_data()
    msg_ids = data.get(key, [])
    if not msg_ids:
        return

    for msg_id in msg_ids:
        await safe_delete_message(bot, chat_id, msg_id)

    await state.update_data({key: []})
