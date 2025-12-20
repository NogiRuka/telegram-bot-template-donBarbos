#!/usr/bin/env python3
"""
测试剧集通知功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from bot.core.emby import EmbyClient
from bot.core.config import settings


async def test_series_notification():
    """测试剧集通知功能
    
    功能说明:
    - 测试获取剧集信息
    - 验证剧集相关字段
    """
    
    client = EmbyClient(
        base_url=settings.EMBY_BASE_URL,
        api_key=settings.EMBY_API_KEY
    )
    
    try:
        # 使用日志中的实际数据
        series_id = "12776"  # 从日志中获取的SeriesId
        episode_id = "12784"  # 从日志中获取的ItemId
        
        print("🧪 测试剧集通知功能...")
        print(f"📺 剧集ID: {series_id}")
        print(f"📺 剧集ID: {episode_id}")
        print("-" * 50)
        
        # 测试获取剧集信息
        user_id = settings.get_emby_template_user_id() or str(settings.get_owner_id())
        series_info = await client.get_series_info(user_id, series_id)
        if series_info:
            print("✅ 成功获取剧集信息:")
            print(f"  📖 剧集名称: {series_info.get('Name', 'N/A')}")
            print(f"  🏷️ 类型: {series_info.get('Type', 'N/A')}")
            print(f"  🆔 ID: {series_info.get('Id', 'N/A')}")
            if series_info.get('Overview'):
                print(f"  📝 简介: {series_info['Overview'][:100]}...")
        else:
            print("❌ 无法获取剧集信息")
            
        print()
        
        # 测试获取单集信息
        episode_info = await client.get_item(user_id, episode_id)
        if episode_info:
            print("✅ 成功获取单集信息:")
            print(f"  📖 单集名称: {episode_info.get('Name', 'N/A')}")
            print(f"  📺 剧集名称: {episode_info.get('SeriesName', 'N/A')}")
            print(f"  🆔 剧集ID: {episode_info.get('SeriesId', 'N/A')}")
            print(f"  🆔 季ID: {episode_info.get('SeasonId', 'N/A')}")
            print(f"  📅 季号: {episode_info.get('ParentIndexNumber', 'N/A')}")
            print(f"  📺 集号: {episode_info.get('IndexNumber', 'N/A')}")
            print(f"  🏷️ 季名称: {episode_info.get('SeasonName', 'N/A')}")
        else:
            print("❌ 无法获取单集信息")
            
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(test_series_notification())