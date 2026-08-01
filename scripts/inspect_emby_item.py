"""inspect_emby_item.py

只读联调脚本：读取指定 Item 的完整 DTO，打印字段结构，用于整理可更新属性清单。

用法:
    python -m scripts.inspect_emby_item [item_id]
    默认 item_id = 26222
"""

from __future__ import annotations

import asyncio
import json
import sys

from bot.utils.emby import get_emby_client


async def main(item_id: str) -> None:
    client = get_emby_client()
    if client is None:
        print("Emby 未配置（EMBY_BASE_URL / EMBY_API_KEY 缺失）")
        return

    # 1. 连接测试
    info = await client.get_system_info()
    print("=== System Info ===")
    print(json.dumps(info, ensure_ascii=False, indent=2))

    # 2. 取一个可用用户作为上下文
    users, _ = await client.get_users(is_disabled=False, limit=1)
    if not users:
        print("无可用用户，无法读取 Item")
        return
    user = users[0]
    user_id = user.get("Id")
    print(f"\n=== 上下文用户: {user.get('Name')} ({user_id}) ===")

    # 3. 读取 Item 完整 DTO
    item = await client.get_item(user_id, item_id)
    print(f"\n=== Item {item_id} 完整 DTO（{len(item)} 个字段）===")
    print(json.dumps(item, ensure_ascii=False, indent=2))

    # 4. 字段摘要（键 / 类型 / 预览值）
    print(f"\n=== 字段摘要（{len(item)} 项）===")
    for key, value in item.items():
        vtype = type(value).__name__
        preview = str(value).replace("\n", " ")[:100]
        print(f"{key}\t[{vtype}]\t{preview}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "26222"
    asyncio.run(main(target))
