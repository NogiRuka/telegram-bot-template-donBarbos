"""
Chat信息测试Handler

通过bot命令来测试获取chat信息
"""
import json

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from bot.tests.chat_info_test import ChatInfoTester

router = Router()


@router.message(Command("chatinfo"))
async def cmd_chat_info(message: Message) -> None:
    """
    获取当前聊天信息的命令

    使用方法: /chatinfo
    """
    try:
        # 看看message包含什么
        logger.debug(f"message 对象: {message}")
        logger.debug(f"message.chat: {message.chat}")
        logger.debug(f"message.from_user: {message.from_user}")

        tester = ChatInfoTester()

        # 获取当前聊天的信息
        chat_id = message.chat.id
        result = await tester.get_chat_info(chat_id)

        # 格式化输出
        if result["success"]:
            response = "✅ <b>Chat信息获取成功</b>\n\n"
            response += f"<b>Chat ID:</b> <code>{result['chat_id']}</code>\n"

            if result["chat_info"]:
                chat_info = result["chat_info"]
                response += f"<b>类型:</b> {chat_info.get('type', 'N/A')}\n"
                response += f"<b>标题:</b> {chat_info.get('title', 'N/A')}\n"
                response += f"<b>用户名:</b> @{chat_info.get('username', 'N/A')}\n"
                response += f"<b>名字:</b> {chat_info.get('first_name', 'N/A')}\n"
                response += f"<b>姓氏:</b> {chat_info.get('last_name', 'N/A')}\n"

                if chat_info.get("description"):
                    response += f"<b>描述:</b> {chat_info['description']}\n"

                if chat_info.get("bio"):
                    response += f"<b>个人简介:</b> {chat_info['bio']}\n"

            if result.get("member_count"):
                response += f"<b>成员数量:</b> {result['member_count']}\n"

            response += f"\n<b>可用方法:</b> {', '.join(result['available_methods'])}\n"

            # 如果消息太长，分段发送
            if len(response) > 4000:
                await message.answer(response[:4000])

                # 发送详细的JSON数据
                json_data = json.dumps(result, indent=2, ensure_ascii=False)
                if len(json_data) > 4000:
                    # 如果JSON数据也太长，截断
                    json_data = json_data[:3900] + "\n...(数据被截断)"

                await message.answer(f"<b>详细数据:</b>\n<pre>{json_data}</pre>")
            else:
                await message.answer(response)
        else:
            response = "❌ <b>获取Chat信息失败</b>\n\n"
            response += f"<b>Chat ID:</b> <code>{result['chat_id']}</code>\n"
            response += f"<b>错误:</b> {result['error']}\n"
            await message.answer(response)

        await tester.close()

    except Exception as e:
        logger.error(f"处理chatinfo命令时出错: {e}")
        await message.answer(f"❌ 处理命令时出错: {e!s}")


@router.message(Command("testchat"))
async def cmd_test_chat(message: Message) -> None:
    """
    测试指定chat_id的信息

    使用方法: /testchat <chat_id>
    例如: /testchat 123456789
    """
    try:
        # 解析命令参数
        args = message.text.split()[1:] if message.text else []

        if not args:
            await message.answer(
                "❌ <b>使用方法错误</b>\n\n"
                "请提供要测试的chat_id:\n"
                "<code>/testchat 123456789</code>\n"
                "<code>/testchat @username</code>"
            )
            return

        chat_id = args[0]

        # 尝试转换为整数
        try:
            if not chat_id.startswith("@"):
                chat_id = int(chat_id)
        except ValueError:
            pass

        tester = ChatInfoTester()

        await message.answer(f"🔍 正在测试 chat_id: <code>{chat_id}</code>...")

        # 获取指定聊天的信息
        result = await tester.get_chat_info(chat_id)

        # 格式化输出
        if result["success"]:
            response = "✅ <b>Chat信息获取成功</b>\n\n"
            response += f"<b>Chat ID:</b> <code>{result['chat_id']}</code>\n"

            if result["chat_info"]:
                chat_info = result["chat_info"]
                response += f"<b>类型:</b> {chat_info.get('type', 'N/A')}\n"
                response += f"<b>标题:</b> {chat_info.get('title', 'N/A')}\n"
                response += f"<b>用户名:</b> @{chat_info.get('username', 'N/A')}\n"
                response += f"<b>名字:</b> {chat_info.get('first_name', 'N/A')}\n"
                response += f"<b>姓氏:</b> {chat_info.get('last_name', 'N/A')}\n"

                if chat_info.get("description"):
                    response += f"<b>描述:</b> {chat_info['description'][:100]}{'...' if len(chat_info['description']) > 100 else ''}\n"

                if chat_info.get("bio"):
                    response += f"<b>个人简介:</b> {chat_info['bio'][:100]}{'...' if len(chat_info['bio']) > 100 else ''}\n"

            if result.get("member_count"):
                response += f"<b>成员数量:</b> {result['member_count']}\n"

            if result.get("administrators"):
                response += f"<b>管理员数量:</b> {len(result['administrators'])}\n"

            response += f"\n<b>可用方法:</b> {', '.join(result['available_methods'])}\n"

            await message.answer(response)

            # 发送详细的JSON数据（如果不是太长）
            json_data = json.dumps(result, indent=2, ensure_ascii=False)
            if len(json_data) <= 4000:
                await message.answer(f"<b>详细数据:</b>\n<pre>{json_data}</pre>")
            else:
                await message.answer("📄 详细数据太长，已省略。可以查看日志获取完整信息。")
                logger.info(f"Chat {chat_id} 详细信息: {json_data}")
        else:
            response = "❌ <b>获取Chat信息失败</b>\n\n"
            response += f"<b>Chat ID:</b> <code>{result['chat_id']}</code>\n"
            response += f"<b>错误:</b> {result['error']}\n"
            await message.answer(response)

        await tester.close()

    except Exception as e:
        logger.error(f"处理testchat命令时出错: {e}")
        await message.answer(f"❌ 处理命令时出错: {e!s}")


@router.message(Command("myinfo"))
async def cmd_my_info(message: Message) -> None:
    """
    获取发送者的用户信息

    使用方法: /myinfo
    """
    try:
        user = message.from_user
        chat = message.chat

        response = "👤 <b>您的信息</b>\n\n"
        response += f"<b>用户ID:</b> <code>{user.id}</code>\n"
        response += f"<b>名字:</b> {user.first_name}\n"
        response += f"<b>姓氏:</b> {user.last_name or 'N/A'}\n"
        response += f"<b>用户名:</b> @{user.username or 'N/A'}\n"
        response += f"<b>语言:</b> {user.language_code or 'N/A'}\n"
        response += f"<b>是否为Bot:</b> {'是' if user.is_bot else '否'}\n"
        response += f"<b>是否为高级用户:</b> {'是' if getattr(user, 'is_premium', False) else '否'}\n"

        response += "\n💬 <b>当前聊天信息</b>\n"
        response += f"<b>聊天ID:</b> <code>{chat.id}</code>\n"
        response += f"<b>聊天类型:</b> {chat.type}\n"
        response += f"<b>聊天标题:</b> {chat.title or 'N/A'}\n"

        await message.answer(response)

    except Exception as e:
        logger.error(f"处理myinfo命令时出错: {e}")
        await message.answer(f"❌ 处理命令时出错: {e!s}")


@router.message(Command("messageinfo"))
async def cmd_message_info(message: Message) -> None:
    """
    获取消息详细信息

    使用方法: /messageinfo <chat_id> <message_id>
    """
    try:
        # 解析命令参数
        args = message.text.split()[1:] if message.text else []

        if len(args) < 2:
            await message.answer(
                "❌ <b>使用方法错误</b>\n\n"
                "请提供chat_id和message_id:\n"
                "<code>/messageinfo &lt;chat_id&gt; &lt;message_id&gt;</code>\n\n"
                "<b>示例:</b>\n"
                "• <code>/messageinfo -1001234567890 123</code> - 获取群组消息\n"
                "• <code>/messageinfo @username 456</code> - 获取用户消息\n"
                "• <code>/messageinfo 123456789 789</code> - 获取私聊消息"
            )
            return

        chat_id_str = args[0]
        try:
            message_id = int(args[1])
        except ValueError:
            await message.answer("❌ message_id 必须是数字")
            return

        # 处理chat_id
        if chat_id_str.startswith("@"):
            chat_id = chat_id_str
        else:
            try:
                chat_id = int(chat_id_str)
            except ValueError:
                await message.answer("❌ chat_id 格式错误，应该是数字或@username")
                return

        # 创建测试器并获取消息信息
        tester = ChatInfoTester()

        await message.answer("🔍 正在获取消息信息...")

        result = await tester.get_message_info(chat_id, message_id)

        if result["success"]:
            msg_info = result["message_info"]

            # 构建响应消息
            response_parts = [
                "✅ <b>消息信息获取成功</b>\n",
                f"<b>Chat ID:</b> <code>{result['chat_id']}</code>",
                f"<b>Message ID:</b> <code>{result['message_id']}</code>",
                f"<b>内容类型:</b> {msg_info.get('content_type', 'unknown')}",
                f"<b>发送时间:</b> {msg_info.get('date', 'unknown')}",
            ]

            # 发送者信息
            if msg_info.get("from_user"):
                user = msg_info["from_user"]
                user_info = f"<b>发送者:</b> {user.get('first_name', '')} {user.get('last_name', '') or ''}".strip()
                if user.get("username"):
                    user_info += f" (@{user['username']})"
                user_info += f" [ID: <code>{user['id']}</code>]"
                if user.get("is_bot"):
                    user_info += " 🤖"
                if user.get("is_premium"):
                    user_info += " ⭐"
                response_parts.append(user_info)

            # 聊天信息
            chat = msg_info.get("chat", {})
            chat_info = f"<b>聊天:</b> {chat.get('type', 'unknown')}"
            if chat.get("title"):
                chat_info += f" - {chat['title']}"
            elif chat.get("first_name"):
                chat_info += f" - {chat['first_name']} {chat.get('last_name', '') or ''}".strip()
            if chat.get("username"):
                chat_info += f" (@{chat['username']})"
            response_parts.append(chat_info)

            # 消息内容
            if msg_info.get("text"):
                content = msg_info["text"]
                if len(content) > 200:
                    content = content[:200] + "..."
                response_parts.append(f"<b>文本内容:</b> {content}")
            elif msg_info.get("caption"):
                caption = msg_info["caption"]
                if len(caption) > 200:
                    caption = caption[:200] + "..."
                response_parts.append(f"<b>媒体标题:</b> {caption}")

            # 媒体信息
            if msg_info.get("media"):
                media = msg_info["media"]
                media_info = f"<b>媒体类型:</b> {media.get('type', 'unknown')}"
                if media.get("file_size"):
                    media_info += f" ({media['file_size']} bytes)"
                if media.get("duration"):
                    media_info += f" - 时长: {media['duration']}秒"
                if media.get("width") and media.get("height"):
                    media_info += f" - 尺寸: {media['width']}x{media['height']}"
                response_parts.append(media_info)

            # 回复信息
            if msg_info.get("reply_to_message"):
                reply = msg_info["reply_to_message"]
                response_parts.append(f"<b>回复消息:</b> ID <code>{reply['message_id']}</code>")

            # 转发信息
            if msg_info.get("forward_info"):
                forward = msg_info["forward_info"]
                if forward["type"] == "user":
                    user = forward["from_user"]
                    response_parts.append(f"<b>转发自用户:</b> {user['first_name']} (@{user.get('username', 'N/A')})")
                elif forward["type"] == "chat":
                    chat = forward["from_chat"]
                    response_parts.append(f"<b>转发自聊天:</b> {chat.get('title', 'N/A')} ({chat['type']})")

            # 实体信息
            if msg_info.get("entities"):
                entities = [f"{e['type']}({e['offset']}-{e['offset']+e['length']})" for e in msg_info["entities"]]
                response_parts.append(f"<b>格式化实体:</b> {', '.join(entities)}")

            # 其他信息
            if msg_info.get("edit_date"):
                response_parts.append(f"<b>编辑时间:</b> {msg_info['edit_date']}")
            if msg_info.get("media_group_id"):
                response_parts.append(f"<b>媒体组ID:</b> <code>{msg_info['media_group_id']}</code>")
            if msg_info.get("has_protected_content"):
                response_parts.append("<b>受保护内容:</b> ✅")

            response = "\n".join(response_parts)

            # 分割长消息
            if len(response) > 4000:
                parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for i, part in enumerate(parts):
                    if i == 0:
                        await message.answer(part)
                    else:
                        await message.answer(f"<b>续 {i+1}:</b>\n{part}")
            else:
                await message.answer(response)
        else:
            await message.answer(
                f"❌ <b>获取消息信息失败</b>\n\n"
                f"<b>Chat ID:</b> <code>{result['chat_id']}</code>\n"
                f"<b>Message ID:</b> <code>{result['message_id']}</code>\n"
                f"<b>错误:</b> {result['error']}"
            )

        await tester.close()

    except Exception as e:
        logger.error(f"处理messageinfo命令时出错: {e}")
        await message.answer(f"❌ 处理命令时发生错误: {e!s}")


@router.message(Command("testhelp"))
async def cmd_test_help(message: Message) -> None:
    """
    显示测试命令帮助

    使用方法: /testhelp
    """
    help_text = """
🧪 <b>Chat信息测试命令</b>

<b>/chatinfo</b> - 获取当前聊天的详细信息
<b>/testchat &lt;chat_id&gt;</b> - 测试指定chat_id的信息
<b>/myinfo</b> - 获取您的用户信息
<b>/messageinfo &lt;chat_id&gt; &lt;message_id&gt;</b> - 获取指定消息的详细信息
<b>/testhelp</b> - 显示此帮助信息

<b>示例:</b>
<code>/testchat 123456789</code>
<code>/testchat @username</code>
<code>/testchat -1001234567890</code>
<code>/messageinfo -1001234567890 123</code>
<code>/messageinfo @username 456</code>

<b>注意:</b>
• 只能获取bot有权限访问的聊天信息
• 私聊需要用户先与bot对话
• 群组需要bot是成员
• 频道需要bot是管理员
• 获取消息信息需要转发权限
"""

    await message.answer(help_text)
