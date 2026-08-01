"""test_emby_upload_image.py

upload_item_image 诊断测试：尝试直接 POST、DELETE+POST 两种方式，打印返回值与 ImageTags 变化。

用法:
    uv run python -m scripts.test_emby_upload_image [item_id] [image_path]
    默认 item_id = 26222, image_path = assets/ui/start.jpg
"""

from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path

from bot.utils.emby import get_emby_client


async def fetch_tags(client, user_id, item_id):
    item = await client.get_item(user_id, item_id)
    return item.get("ImageTags", {})


async def main(item_id: str, image_path: str) -> None:
    client = get_emby_client()
    if client is None:
        print("Emby 未配置")
        return

    p = Path(image_path)
    if not p.exists():
        print(f"图片不存在: {p}")
        return
    b64 = base64.b64encode(p.read_bytes()).decode()
    print(f"[1] 已读取图片 {p}（{len(b64)} 字符 base64）")

    users, _ = await client.get_users(limit=1)
    user_id = users[0]["Id"]
    before = await fetch_tags(client, user_id, item_id)
    print(f"[2] 上传前 ImageTags: {before}")

    # 方式一：直接 POST（打印返回值）
    print("[3a] 直接 POST ...")
    try:
        ret = await client.upload_item_image(item_id, b64, "Primary")
        print(f"     返回值: {ret!r}")
    except Exception as e:
        print(f"     异常: {e}")
    await asyncio.sleep(1)
    after_direct = await fetch_tags(client, user_id, item_id)
    print(f"     直接 POST 后 ImageTags: {after_direct}")

    # 方式二：DELETE 再 POST
    print("[3b] DELETE 再 POST ...")
    try:
        ret_del = await client.http.request("DELETE", f"/Items/{item_id}/Images/Primary")
        print(f"     DELETE 返回值: {ret_del!r}")
    except Exception as e:
        print(f"     DELETE 异常: {e}")
    try:
        ret_post = await client.upload_item_image(item_id, b64, "Primary")
        print(f"     POST 返回值: {ret_post!r}")
    except Exception as e:
        print(f"     POST 异常: {e}")
    await asyncio.sleep(1)
    after_replace = await fetch_tags(client, user_id, item_id)
    print(f"     DELETE+POST 后 ImageTags: {after_replace}")

    # 结论
    print("\n=== 结论 ===")
    if before.get("Primary") != after_replace.get("Primary"):
        print("✅ Primary 哈希已变化（DELETE+POST 生效）")
    elif before.get("Primary") != after_direct.get("Primary"):
        print("✅ Primary 哈希已变化（直接 POST 生效）")
    else:
        print("⚠️ Primary 哈希始终未变，上传可能未真正写入")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "26222"
    img = sys.argv[2] if len(sys.argv) > 2 else "assets/ui/start.jpg"
    asyncio.run(main(target, img))
