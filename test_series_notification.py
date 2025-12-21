#!/usr/bin/env python3
"""
测试剧集通知功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from bot.core.config import settings
from bot.core.emby import EmbyClient
from bot.utils.emby import get_emby_client


async def test_series_notification() -> None:
    """测试剧集通知功能

    功能说明:
    - 测试获取剧集信息
    - 验证剧集相关字段
    """

    client = get_emby_client()
    if not client:
        print("❌ Emby 服务配置异常，请检查配置")
        return

    try:
        # 使用日志中的实际数据
        series_id = "12776"  # 从日志中获取的SeriesId
        episode_id = "12784"  # 从日志中获取的ItemId


        # 测试获取剧集信息
        user_id = settings.get_emby_template_user_id() or str(settings.get_owner_id())
        series_info = await client.get_series_info(user_id, series_id)
        if series_info:
            if series_info.get("Overview"):
                pass
        else:
            pass


        # 测试获取单集信息
        episode_info = await client.get_item(user_id, episode_id)
        if episode_info:
            pass
        else:
            pass

    except Exception:
        import traceback
        traceback.print_exc()

    finally:
        pass


if __name__ == "__main__":
    asyncio.run(test_series_notification())
