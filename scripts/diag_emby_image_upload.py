"""diag_emby_image_upload.py

绕过 HttpClient，直接用 aiohttp 调用 Emby 图片上传，打印完整 status/headers/body 诊断。
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

import aiohttp

from bot.core.config import settings


async def main() -> None:
    base = settings.get_emby_base_url().rstrip("/")
    token = settings.get_emby_api_key()
    item_id = "26222"
    img_path = "assets/ui/start.jpg"

    b64 = base64.b64encode(Path(img_path).read_bytes()).decode()
    url = f"{base}/emby/Items/{item_id}/Images/Primary"
    headers = {"X-Emby-Token": token, "Content-Type": "image/jpeg"}

    print(f"URL: {url}")
    print(f"base64 长度: {len(b64)}")

    async with aiohttp.ClientSession() as s:
        # 先 DELETE
        async with s.delete(url, headers={"X-Emby-Token": token}) as r:
            print(f"\n[DELETE] status={r.status}")
            print(f"  headers={dict(r.headers)}")
            print(f"  body={(await r.text())[:200]!r}")

        await asyncio.sleep(1)

        # 再 POST 原生 base64
        async with s.post(url, headers=headers, data=b64) as r:
            print(f"\n[POST raw base64] status={r.status}")
            print(f"  headers={dict(r.headers)}")
            print(f"  body={(await r.text())[:500]!r}")

        await asyncio.sleep(1)

        # 复查
        async with s.get(
            f"{base}/emby/Users/Query",
            params={"IsDisabled": "false", "Limit": "1"},
            headers={"X-Emby-Token": token},
        ) as r:
            users = await r.json()
        uid = users["Items"][0]["Id"]

        async with s.get(
            f"{base}/emby/Users/{uid}/Items/{item_id}",
            headers={"X-Emby-Token": token},
        ) as r:
            item = await r.json()
        print(f"\n[复查] ImageTags={item.get('ImageTags')}")

        # 直接拉图片看长度
        async with s.get(
            f"{base}/emby/Items/{item_id}/Images/Primary",
            headers={"X-Emby-Token": token},
        ) as r:
            data = await r.read()
            print(f"[图片] Primary 实际返回 {len(data)} 字节, 头={data[:8].hex() if data else 'empty'}")


if __name__ == "__main__":
    asyncio.run(main())
