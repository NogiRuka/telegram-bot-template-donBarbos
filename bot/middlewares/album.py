import asyncio
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 1) -> None: # 稍微加长到0.6s，确保相册收全
        self.latency = latency
        self.cache: dict[str, list[Message]] = {}

    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.media_group_id:
            return await handler(event, data)

        mid = event.media_group_id

        # 如果是该相册的第一条消息
        if mid not in self.cache:
            self.cache[mid] = [event]
            await asyncio.sleep(self.latency)

            # 收集完毕，准备传给 Handler
            data["album"] = self.cache.pop(mid)
            return await handler(event, data)

        # 如果是后续消息，直接加入缓存并终止本次链路（不进入后面的 Throttling 和 Handler）
        self.cache[mid].append(event)
        return None # 关键：这里不执行 handler，这样就不会触发频率限制和多次保存
