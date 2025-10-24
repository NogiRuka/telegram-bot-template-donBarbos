#!/usr/bin/env python3
"""
独立的Chat信息测试运行脚本

可以直接运行此脚本来测试aiogram获取chat信息的功能
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bot.tests.chat_info_test import ChatInfoTester
from loguru import logger


async def test_current_user():
    """测试获取当前用户（bot自己）的信息"""
    print("\n" + "="*50)
    print("🤖 测试Bot自身信息")
    print("="*50)
    
    tester = ChatInfoTester()
    
    try:
        # 获取bot自己的信息
        bot_info = await tester.bot.get_me()
        print(f"✅ Bot信息获取成功:")
        print(f"   ID: {bot_info.id}")
        print(f"   用户名: @{bot_info.username}")
        print(f"   名字: {bot_info.first_name}")
        print(f"   是否为Bot: {bot_info.is_bot}")
        print(f"   支持内联查询: {getattr(bot_info, 'supports_inline_queries', False)}")
        print(f"   可以加入群组: {getattr(bot_info, 'can_join_groups', False)}")
        print(f"   可以读取所有群组消息: {getattr(bot_info, 'can_read_all_group_messages', False)}")
        
    except Exception as e:
        print(f"❌ 获取Bot信息失败: {e}")
    
    await tester.close()


async def test_specific_chats():
    """测试特定的chat_id"""
    print("\n" + "="*50)
    print("🔍 测试特定Chat ID")
    print("="*50)
    
    # 这里可以添加一些已知的chat_id进行测试
    test_chat_ids = [
        # 可以添加一些测试用的chat_id
        # 例如: 123456789, "@username", -1001234567890
    ]
    
    if not test_chat_ids:
        print("ℹ️  没有配置测试用的chat_id")
        print("   可以在 test_chat_ids 列表中添加要测试的chat_id")
        return
    
    tester = ChatInfoTester()
    
    for chat_id in test_chat_ids:
        print(f"\n🔍 测试 chat_id: {chat_id}")
        result = await tester.get_chat_info(chat_id)
        
        if result["success"]:
            print(f"✅ 成功获取信息:")
            if result["chat_info"]:
                chat_info = result["chat_info"]
                print(f"   类型: {chat_info.get('type', 'N/A')}")
                print(f"   标题: {chat_info.get('title', 'N/A')}")
                print(f"   用户名: @{chat_info.get('username', 'N/A')}")
                print(f"   名字: {chat_info.get('first_name', 'N/A')}")
            
            if result.get("member_count"):
                print(f"   成员数量: {result['member_count']}")
            
            print(f"   可用方法: {', '.join(result['available_methods'])}")
        else:
            print(f"❌ 获取失败: {result['error']}")
    
    await tester.close()


async def interactive_test():
    """交互式测试"""
    print("\n" + "="*50)
    print("🎮 交互式Chat信息测试")
    print("="*50)
    print("输入要测试的chat_id，输入 'quit' 退出")
    print("支持格式:")
    print("  - 数字ID: 123456789")
    print("  - 用户名: @username")
    print("  - 群组ID: -1001234567890")
    print("  - 'me' 获取bot自身信息")
    
    tester = ChatInfoTester()
    
    while True:
        try:
            chat_input = input("\n请输入chat_id: ").strip()
            
            if chat_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not chat_input:
                continue
            
            if chat_input.lower() == 'me':
                # 获取bot自己的信息
                try:
                    bot_info = await tester.bot.get_me()
                    print(f"✅ Bot信息:")
                    print(f"   ID: {bot_info.id}")
                    print(f"   用户名: @{bot_info.username}")
                    print(f"   名字: {bot_info.first_name}")
                    print(f"   是否为Bot: {bot_info.is_bot}")
                except Exception as e:
                    print(f"❌ 获取Bot信息失败: {e}")
                continue
            
            # 尝试转换为整数
            chat_id = chat_input
            try:
                if not chat_id.startswith('@'):
                    chat_id = int(chat_id)
            except ValueError:
                pass
            
            print(f"🔍 正在测试 {chat_id}...")
            result = await tester.get_chat_info(chat_id)
            
            if result["success"]:
                print(f"✅ 成功获取信息:")
                print(f"   Chat ID: {result['chat_id']}")
                
                if result["chat_info"]:
                    chat_info = result["chat_info"]
                    print(f"   类型: {chat_info.get('type', 'N/A')}")
                    print(f"   标题: {chat_info.get('title', 'N/A')}")
                    print(f"   用户名: @{chat_info.get('username', 'N/A')}")
                    print(f"   名字: {chat_info.get('first_name', 'N/A')}")
                    print(f"   姓氏: {chat_info.get('last_name', 'N/A')}")
                    
                    if chat_info.get('description'):
                        desc = chat_info['description']
                        if len(desc) > 100:
                            desc = desc[:100] + "..."
                        print(f"   描述: {desc}")
                    
                    if chat_info.get('bio'):
                        bio = chat_info['bio']
                        if len(bio) > 100:
                            bio = bio[:100] + "..."
                        print(f"   个人简介: {bio}")
                
                if result.get("member_count"):
                    print(f"   成员数量: {result['member_count']}")
                
                if result.get("administrators"):
                    print(f"   管理员数量: {len(result['administrators'])}")
                
                print(f"   可用方法: {', '.join(result['available_methods'])}")
                
                # 询问是否显示详细信息
                show_detail = input("是否显示详细JSON信息? (y/N): ").strip().lower()
                if show_detail in ['y', 'yes']:
                    import json
                    print("\n📄 详细信息:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"❌ 获取失败: {result['error']}")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出测试")
            break
        except Exception as e:
            print(f"❌ 处理输入时出错: {e}")
    
    await tester.close()


async def test_message_info():
    """测试消息信息"""
    print("\n" + "="*50)
    print("📨 测试消息信息")
    print("="*50)
    
    try:
        chat_id_input = input("请输入chat_id: ").strip()
        message_id_input = input("请输入message_id: ").strip()
        
        if not chat_id_input or not message_id_input:
            print("❌ 请输入完整的chat_id和message_id")
            return
        
        # 解析输入
        try:
            if chat_id_input.startswith('@'):
                chat_id = chat_id_input
            else:
                chat_id = int(chat_id_input)
            message_id = int(message_id_input)
        except ValueError:
            print("❌ ID格式错误")
            return
        
        tester = ChatInfoTester()
        print(f"🔍 正在获取消息信息: chat_id={chat_id}, message_id={message_id}")
        result = await tester.get_message_info(chat_id, message_id)
        
        # 格式化输出
        print("\n" + "="*50)
        print(f"消息信息测试结果")
        print("="*50)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        await tester.close()
        
    except Exception as e:
        print(f"❌ 测试消息信息时发生错误: {e}")


async def interactive_message_test():
    """交互式消息测试"""
    print("\n" + "="*50)
    print("🎮 交互式消息测试")
    print("="*50)
    print("输入要测试的chat_id和message_id，输入 'quit' 退出")
    
    tester = ChatInfoTester()
    
    while True:
        try:
            chat_id_input = input("\n请输入chat_id: ").strip()
            
            if chat_id_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not chat_id_input:
                continue
            
            message_id_input = input("请输入message_id: ").strip()
            
            if not message_id_input:
                print("❌ 请输入有效的message_id")
                continue
            
            # 解析输入
            try:
                if chat_id_input.startswith('@'):
                    chat_id = chat_id_input
                else:
                    chat_id = int(chat_id_input)
                message_id = int(message_id_input)
            except ValueError:
                print("❌ ID格式错误，应该是数字或@username")
                continue
            
            print(f"🔍 正在获取消息信息: chat_id={chat_id}, message_id={message_id}")
            result = await tester.get_message_info(chat_id, message_id)
            
            # 格式化输出
            print("\n" + "="*30)
            print(f"消息信息: {chat_id}/{message_id}")
            print("="*30)
            
            if result.get("success"):
                print("✅ 成功获取消息信息:")
                if result.get("message_info"):
                    msg_info = result["message_info"]
                    print(f"   消息ID: {msg_info.get('message_id', 'N/A')}")
                    print(f"   发送者: {msg_info.get('from_user', 'N/A')}")
                    print(f"   日期: {msg_info.get('date', 'N/A')}")
                    print(f"   文本: {msg_info.get('text', 'N/A')[:100]}..." if msg_info.get('text') else "   文本: 无")
                    print(f"   消息类型: {msg_info.get('content_type', 'N/A')}")
                
                # 询问是否显示详细信息
                show_detail = input("是否显示详细JSON信息? (y/N): ").strip().lower()
                if show_detail in ['y', 'yes']:
                    import json
                    print("\n📄 详细信息:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"❌ 获取失败: {result.get('error', '未知错误')}")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出测试")
            break
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
    
    await tester.close()


async def main():
    """主函数"""
    print("🧪 Aiogram Chat信息测试工具")
    print("="*50)
    
    # 检查配置
    try:
        from bot.core.config import settings
        if not settings.BOT_TOKEN:
            print("❌ 错误: 未配置Bot Token")
            print("请在 .env 文件中设置 BOT_TOKEN")
            return
        
        print(f"✅ Bot Token已配置")
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return
    
    # 显示菜单
    while True:
        print("\n请选择测试模式:")
        print("1. 测试Bot自身信息")
        print("2. 测试特定Chat ID")
        print("3. 交互式测试")
        print("4. 测试消息信息")
        print("5. 交互式消息测试")
        print("6. 退出")
        
        try:
            choice = input("\n请输入选择 (1-6): ").strip()
            
            if choice == '1':
                await test_current_user()
            elif choice == '2':
                await test_specific_chats()
            elif choice == '3':
                await interactive_test()
            elif choice == '4':
                await test_message_info()
            elif choice == '5':
                await interactive_message_test()
            elif choice == '6':
                print("👋 退出测试")
                break
            else:
                print("❌ 无效选择，请输入 1-6")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"❌ 程序出错: {e}")
            logger.exception("程序异常")


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被中断")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        logger.exception("程序启动异常")