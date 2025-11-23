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

import contextlib

from loguru import logger

from bot.tests.chat_info_test import ChatInfoTester


async def test_current_user() -> None:
    """测试获取当前用户（bot自己）的信息"""

    tester = ChatInfoTester()

    try:
        # 获取bot自己的信息
        await tester.bot.get_me()

    except Exception:
        pass

    await tester.close()


async def test_specific_chats() -> None:
    """测试特定的chat_id"""

    # 这里可以添加一些已知的chat_id进行测试
    test_chat_ids = [
        # 可以添加一些测试用的chat_id
        # 例如: 123456789, "@username", -1001234567890
    ]

    if not test_chat_ids:
        return

    tester = ChatInfoTester()

    for chat_id in test_chat_ids:
        result = await tester.get_chat_info(chat_id)

        if result["success"]:
            if result["chat_info"]:
                result["chat_info"]

            if result.get("member_count"):
                pass

        else:
            pass

    await tester.close()


async def interactive_test() -> None:
    """交互式测试"""

    tester = ChatInfoTester()

    while True:
        try:
            chat_input = input("\n请输入chat_id: ").strip()

            if chat_input.lower() in ["quit", "exit", "q"]:
                break

            if not chat_input:
                continue

            if chat_input.lower() == "me":
                # 获取bot自己的信息
                with contextlib.suppress(Exception):
                    await tester.bot.get_me()
                continue

            # 尝试转换为整数
            chat_id = chat_input
            try:
                if not chat_id.startswith("@"):
                    chat_id = int(chat_id)
            except ValueError:
                pass

            result = await tester.get_chat_info(chat_id)

            if result["success"]:

                if result["chat_info"]:
                    chat_info = result["chat_info"]

                    if chat_info.get("description"):
                        desc = chat_info["description"]
                        if len(desc) > 100:
                            desc = desc[:100] + "..."

                    if chat_info.get("bio"):
                        bio = chat_info["bio"]
                        if len(bio) > 100:
                            bio = bio[:100] + "..."

                if result.get("member_count"):
                    pass

                if result.get("administrators"):
                    pass


                # 询问是否显示详细信息
                show_detail = input("是否显示详细JSON信息? (y/N): ").strip().lower()
                if show_detail in ["y", "yes"]:
                    pass
            else:
                pass

        except KeyboardInterrupt:
            break
        except Exception:
            pass

    await tester.close()


async def test_message_info() -> None:
    """测试消息信息"""

    try:
        chat_id_input = input("请输入chat_id: ").strip()
        message_id_input = input("请输入message_id: ").strip()

        if not chat_id_input or not message_id_input:
            return

        # 解析输入
        try:
            chat_id = chat_id_input if chat_id_input.startswith("@") else int(chat_id_input)
            message_id = int(message_id_input)
        except ValueError:
            return

        tester = ChatInfoTester()
        await tester.get_message_info(chat_id, message_id)

        # 格式化输出

        await tester.close()

    except Exception:
        pass


async def interactive_message_test() -> None:
    """交互式消息测试"""

    tester = ChatInfoTester()

    while True:
        try:
            chat_id_input = input("\n请输入chat_id: ").strip()

            if chat_id_input.lower() in ["quit", "exit", "q"]:
                break

            if not chat_id_input:
                continue

            message_id_input = input("请输入message_id: ").strip()

            if not message_id_input:
                continue

            # 解析输入
            try:
                chat_id = chat_id_input if chat_id_input.startswith("@") else int(chat_id_input)
                message_id = int(message_id_input)
            except ValueError:
                continue

            result = await tester.get_message_info(chat_id, message_id)

            # 格式化输出

            if result.get("success"):
                if result.get("message_info"):
                    result["message_info"]

                # 询问是否显示详细信息
                show_detail = input("是否显示详细JSON信息? (y/N): ").strip().lower()
                if show_detail in ["y", "yes"]:
                    pass
            else:
                pass

        except KeyboardInterrupt:
            break
        except Exception:
            pass

    await tester.close()


async def main() -> None:
    """主函数"""

    # 检查配置
    try:
        from bot.core.config import settings
        if not settings.BOT_TOKEN:
            return


    except Exception:
        return

    # 显示菜单
    while True:

        try:
            choice = input("\n请输入选择 (1-6): ").strip()

            if choice == "1":
                await test_current_user()
            elif choice == "2":
                await test_specific_chats()
            elif choice == "3":
                await interactive_test()
            elif choice == "4":
                await test_message_info()
            elif choice == "5":
                await interactive_message_test()
            elif choice == "6":
                break
            else:
                pass

        except KeyboardInterrupt:
            break
        except Exception:
            logger.exception("程序异常")


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("程序启动异常")
