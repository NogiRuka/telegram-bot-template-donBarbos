from __future__ import annotations

from bot.utils.http import HttpClient

_hitokoto_client: HttpClient | None = None


def init_hitokoto_client() -> None:
    global _hitokoto_client

    if _hitokoto_client is None:
        _hitokoto_client = HttpClient(
            "https://v1.hitokoto.cn"
        )


def get_hitokoto_client() -> HttpClient:
    if _hitokoto_client is None:
        raise RuntimeError("Hitokoto client 未初始化")
    return _hitokoto_client


async def close_hitokoto_client() -> None:
    global _hitokoto_client

    if _hitokoto_client:
        await _hitokoto_client.close()
        _hitokoto_client = None