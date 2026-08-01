"""diag_emby_image_upload_v2.py

用一张与 26222 现有封面不同的测试图上传，验证 ImageTags 哈希会变化。
复用 get_emby_client 的 HttpClient（有重试）。
"""

from __future__ import annotations

import asyncio
import base64
import io

from bot.utils.emby import get_emby_client


async def main() -> None:
    client = get_emby_client()
    if client is None:
        print("Emby 未配置")
        return
    item_id = "26222"

    # 生成一张与 start.jpg 不同的 100x100 纯色 JPEG
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (100, 100), (12, 74, 107)).save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(f"[1] 生成测试图 100x100（{len(b64)} 字符 base64）")

    users, _ = await client.get_users(limit=1)
    user_id = users[0]["Id"]

    before = (await client.get_item(user_id, item_id)).get("ImageTags", {})
    print(f"[2] 上传前 ImageTags: {before}")

    await client.upload_item_image(item_id, b64, "Primary")
    print("[3] 已 POST 上传")
    await asyncio.sleep(1)

    after = (await client.get_item(user_id, item_id)).get("ImageTags", {})
    print(f"[4] 上传后 ImageTags: {after}")

    if before.get("Primary") != after.get("Primary"):
        print("✅ upload_item_image 验证成功（Primary 哈希已变化）")
    else:
        print("⚠️ Primary 哈希仍未变")


if __name__ == "__main__":
    asyncio.run(main())
