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

from bot.core.emby import EmbyClient
from bot.core.config import settings


async def test_get_item():
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
    emby_client = EmbyClient(
        base_url=settings.EMBY_BASE_URL,
        api_key=settings.EMBY_API_KEY,
    )
    
    try:
        # 测试用的项目ID（需要替换为实际的Emby项目ID）
        test_item_id = "12777"  # 请替换为实际的项目ID
        test_user_id = settings.EMBY_TEMPLATE_USER_ID
        
        print(f"🧪 测试 get_item 接口...")
        print(f"📋 用户ID: {test_user_id}")
        print(f"📁 项目ID: {test_item_id}")
        print(f"🌐 服务器: {settings.EMBY_BASE_URL}")
        print("-" * 50)
        
        # 调用 get_item 接口
        result = await emby_client.get_item(test_user_id, test_item_id)
        
        if result:
            print("✅ 成功获取项目信息！")
            print(f"📊 返回数据类型: {type(result)}")
            print(f"🔑 主要字段:")
            
            # 显示关键信息
            if "Name" in result:
                print(f"  📖 名称: {result['Name']}")
            if "Type" in result:
                print(f"  🏷️ 类型: {result['Type']}")
            if "Id" in result:
                print(f"  🆔 ID: {result['Id']}")
            if "ProductionYear" in result:
                print(f"  📅 年份: {result['ProductionYear']}")
            if "Overview" in result:
                print(f"  📝 简介: {result['Overview'][:100]}...")
                
            # 显示完整的JSON格式数据（缩略）
            import json
            pretty_json = json.dumps(result, ensure_ascii=False, indent=2)
            print(f"\n📄 完整数据（前500字符）:")
            print(pretty_json)
            
        else:
            print("❌ 获取项目信息失败，返回空数据")
            
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 关闭客户端连接
        await emby_client.close()


async def test_get_recent_items():
    """获取最近的项目列表用于测试
    
    功能说明:
    - 获取最近的项目列表，方便选择测试ID
    """
    emby_client = EmbyClient(
        base_url=settings.EMBY_BASE_URL,
        api_key=settings.EMBY_API_KEY,
        user_id=settings.EMBY_ADMIN_ID
    )
    
    try:
        print(f"\n🧪 获取最近项目列表...")
        
        # 获取最近的项目（这里假设有一个获取最近项目的方法）
        # 如果没有，可以手动指定一个已知的项目ID
        user_id = settings.EMBY_ADMIN_ID
        
        # 注意：这里需要根据实际情况调用合适的API
        # 如果 EmbyClient 有其他获取项目列表的方法，可以在这里使用
        print("💡 提示：请手动提供一个有效的项目ID进行测试")
        print("   可以在Emby Web界面中找到项目ID，通常在URL中")
        print("   例如：http://your-emby-server/web/index.html#!/item?id=12345")
        
    except Exception as e:
        print(f"❌ 获取项目列表失败: {e}")
        
    finally:
        await emby_client.close()


async def main():
    """主函数
    
    功能说明:
    - 运行所有测试
    """
    print("🚀 Emby API 测试开始")
    print("=" * 50)
    
    # 检查配置
    if not settings.EMBY_BASE_URL or not settings.EMBY_API_KEY:
        print("❌ 请先配置 EMBY_BASE_URL 和 EMBY_API_KEY")
        return
        
    # 运行测试
    await test_get_item()
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())