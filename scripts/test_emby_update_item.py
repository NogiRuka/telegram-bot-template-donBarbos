"""test_emby_update_item.py

update_item 可逆测试：改 Overview → POST → 复查 → 改回原值，验证写回能力且不留痕。

用法:
    uv run python -m scripts.test_emby_update_item [item_id]
    默认 item_id = 26222
"""

from __future__ import annotations

import asyncio
import copy
import sys

from bot.utils.emby import get_emby_client

MARK = "[GV-TEST 临时标记]"


async def main(item_id: str) -> None:
    client = get_emby_client()
    if client is None:
        print("Emby 未配置")
        return

    users, _ = await client.get_users(limit=1)
    if not users:
        print("无可用用户")
        return
    user_id = users[0]["Id"]

    # 1. 读取原始完整 DTO
    item = await client.get_item(user_id, item_id)
    original_overview = item.get("Overview", "")
    print(f"[1] 原 Overview: {original_overview}")

    # 2. 深拷贝并只改 Overview，整体回写
    patched = copy.deepcopy(item)
    patched["Overview"] = f"{original_overview} {MARK}".strip()
    await client.update_item(item_id, patched)
    print("[2] 已 POST 更新")

    # 3. 复查确认落地
    after = await client.get_item(user_id, item_id)
    after_overview = after.get("Overview", "")
    print(f"[3] 改后 Overview: {after_overview}")
    if MARK not in after_overview:
        print("❌ update_item 未生效")
        return
    print("✅ update_item 验证成功")

    # 4. 改回原值
    restored = copy.deepcopy(after)
    restored["Overview"] = original_overview
    await client.update_item(item_id, restored)
    print("[4] 已改回原值")

    # 5. 最终确认无残留
    final = await client.get_item(user_id, item_id)
    final_overview = final.get("Overview", "")
    print(f"[5] 最终 Overview: {final_overview}")
    if final_overview == original_overview:
        print("✅ 已恢复原状，无残留")
    else:
        print("⚠️ 恢复后与原值不一致，请手动检查")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "26222"
    asyncio.run(main(target))
