"""消息处理工具模块。

这个模块提供与消息相关的通用工具函数，包括消息删除、延迟删除等功能。
适用于整个应用中的消息处理需求。
"""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


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


def delete_message_after_delay(message: Any, delay: int = 3) -> asyncio.Task:
    """延迟指定时间后删除消息，返回异步任务。

    功能说明:
    - 创建异步任务在指定时间后删除消息
    - 自动保存任务引用避免被垃圾回收
    - 适用于发送临时提示消息后自动清理的场景

    输入参数:
    - message: 要删除的消息对象，需要有 delete() 方法
    - delay: 延迟删除的秒数，默认3秒

    返回值:
    - asyncio.Task: 创建的异步任务
    """
    async def _delayed_delete() -> None:
        try:
            await asyncio.sleep(delay)
            await delete_message(message)
        except Exception:
            # 忽略删除过程中的任何错误
            pass

    task = asyncio.create_task(_delayed_delete())
    # 保存任务引用避免被垃圾回收
    task._ignore = True
    return task
