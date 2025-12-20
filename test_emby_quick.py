#!/usr/bin/env python3
"""
Emby API 快速测试命令
提供常用的测试命令示例
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from bot.core.emby import EmbyClient
from bot.core.config import settings


async def quick_test():
    """快速测试 get_item 接口
    
    使用方法:
    1. 修改下面的 item_id 为实际的项目ID
    2. 运行脚本
    
    获取项目ID的方法：
    - 在Emby Web界面中打开一个项目
    - 查看URL中的id参数，如：http://your-emby/web/index.html#!/item?id=12345
    """
    
    # 需要替换为实际的项目ID
    ITEM_ID = "12345"  # ⚠️ 修改这里为你的项目ID
    
    if ITEM_ID == "12345":
        print("⚠️ 请先修改 ITEM_ID 为实际的项目ID")
        print("获取方法：在Emby Web界面中查看项目的URL参数")
        return
    
    client = EmbyClient(
        base_url=settings.EMBY_BASE_URL,
        api_key=settings.EMBY_API_KEY,
        user_id=settings.EMBY_ADMIN_ID
    )
    
    try:
        print(f"🧪 测试 get_item({ITEM_ID})...")
        result = await client.get_item(settings.EMBY_ADMIN_ID, ITEM_ID)
        
        if result:
            print(f"✅ 成功！")
            print(f"📖 名称: {result.get('Name', 'N/A')}")
            print(f"🏷️ 类型: {result.get('Type', 'N/A')}")
            print(f"🆔 ID: {result.get('Id', 'N/A')}")
        else:
            print("❌ 返回空数据")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(quick_test())