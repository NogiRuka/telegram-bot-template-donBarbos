#!/usr/bin/env python3
"""
Emby API 测试脚本
用于测试 get_item 接口
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from bot.core.config import settings
from bot.utils.emby import get_emby_client


async def test_get_item() -> None:
    """测试 get_item 接口

    功能说明:
    - 使用 EmbyClient 获取指定项目的详细信息
    - 需要有效的用户ID和项目ID

    输入参数:
    - 无（使用预设的测试ID）

    返回值:
    - 无（打印测试结果）

    依赖安装方式:
    - 项目依赖已包含在 requirements.txt 中
    """

    # 初始化 Emby 客户端
    emby_client = get_emby_client()
    if not emby_client:
        return

    try:
        # 测试用的项目ID（需要替换为实际的Emby项目ID）
        test_item_id = "12776"  # 请替换为实际的项目ID
        test_user_id = settings.EMBY_TEMPLATE_USER_ID


        # 调用 get_item 接口
        result = await emby_client.get_item(test_user_id, test_item_id)

        if result:

            # 显示关键信息
            if "Name" in result:
                pass
            if "Type" in result:
                pass
            if "Id" in result:
                pass
            if "ProductionYear" in result:
                pass
            if "Overview" in result:
                pass

            # 显示完整的JSON格式数据（缩略）
            import json
            json.dumps(result, ensure_ascii=False, indent=2)

        else:
            pass

    except Exception:
        import traceback
        traceback.print_exc()


async def test_get_recent_items() -> None:
    """获取最近的项目列表用于测试

    功能说明:
    - 获取最近的项目列表，方便选择测试ID
    """
    emby_client = get_emby_client()
    if not emby_client:
        return

    try:

        # 获取最近的项目（这里假设有一个获取最近项目的方法）
        # 如果没有，可以手动指定一个已知的项目ID

        # 注意：这里需要根据实际情况调用合适的API
        # 如果 EmbyClient 有其他获取项目列表的方法，可以在这里使用
        pass

    except Exception:
        pass

    finally:
        await emby_client.close()


async def main() -> None:
    """主函数

    功能说明:
    - 运行所有测试
    """

    # 检查配置
    if not settings.EMBY_BASE_URL or not settings.EMBY_API_KEY:
        return

    # 运行测试
    await test_get_item()



if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
