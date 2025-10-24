"""
Chat ID 信息测试模块

使用 aiogram 测试通过 chat_id 能获取到什么信息
"""
import asyncio
import json
from typing import Dict, Any, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Chat, ChatMember
from loguru import logger

from bot.core.config import settings


class ChatInfoTester:
    """Chat信息测试器"""
    
    def __init__(self, bot_token: str = None):
        """
        初始化测试器
        
        Args:
            bot_token: Bot token，如果不提供则使用配置中的token
        """
        self.bot = Bot(token=bot_token or settings.BOT_TOKEN)
        
    async def get_chat_info(self, chat_id: int | str) -> Dict[str, Any]:
        """
        获取聊天信息
        
        Args:
            chat_id: 聊天ID
            
        Returns:
            Dict[str, Any]: 聊天信息字典
        """
        result = {
            "chat_id": chat_id,
            "success": False,
            "error": None,
            "chat_info": None,
            "chat_member_info": None,
            "available_methods": []
        }
        
        try:
            # 1. 获取基本聊天信息
            logger.info(f"正在获取 chat_id {chat_id} 的基本信息...")
            chat: Chat = await self.bot.get_chat(chat_id)
            
            # 将Chat对象转换为字典
            chat_dict = {
                "id": chat.id,
                "type": chat.type,
                "title": getattr(chat, 'title', None),
                "username": getattr(chat, 'username', None),
                "first_name": getattr(chat, 'first_name', None),
                "last_name": getattr(chat, 'last_name', None),
                "bio": getattr(chat, 'bio', None),
                "description": getattr(chat, 'description', None),
                "invite_link": getattr(chat, 'invite_link', None),
                "pinned_message": getattr(chat, 'pinned_message', None),
                "permissions": getattr(chat, 'permissions', None),
                "slow_mode_delay": getattr(chat, 'slow_mode_delay', None),
                "message_auto_delete_time": getattr(chat, 'message_auto_delete_time', None),
                "has_protected_content": getattr(chat, 'has_protected_content', None),
                "sticker_set_name": getattr(chat, 'sticker_set_name', None),
                "can_set_sticker_set": getattr(chat, 'can_set_sticker_set', None),
                "linked_chat_id": getattr(chat, 'linked_chat_id', None),
                "location": getattr(chat, 'location', None),
                "join_to_send_messages": getattr(chat, 'join_to_send_messages', None),
                "join_by_request": getattr(chat, 'join_by_request', None),
                "has_restricted_voice_and_video_messages": getattr(chat, 'has_restricted_voice_and_video_messages', None),
                "is_forum": getattr(chat, 'is_forum', None),
                "active_usernames": getattr(chat, 'active_usernames', None),
                "emoji_status_custom_emoji_id": getattr(chat, 'emoji_status_custom_emoji_id', None),
                "has_private_forwards": getattr(chat, 'has_private_forwards', None),
                "has_aggressive_anti_spam_enabled": getattr(chat, 'has_aggressive_anti_spam_enabled', None),
            }
            
            result["chat_info"] = chat_dict
            result["available_methods"].append("get_chat")
            
            # 2. 尝试获取聊天成员信息（仅对私聊有效）
            if chat.type == "private":
                try:
                    logger.info(f"正在获取 chat_id {chat_id} 的成员信息...")
                    chat_member: ChatMember = await self.bot.get_chat_member(chat_id, chat_id)
                    
                    member_dict = {
                        "status": chat_member.status,
                        "user": {
                            "id": chat_member.user.id,
                            "is_bot": chat_member.user.is_bot,
                            "first_name": chat_member.user.first_name,
                            "last_name": getattr(chat_member.user, 'last_name', None),
                            "username": getattr(chat_member.user, 'username', None),
                            "language_code": getattr(chat_member.user, 'language_code', None),
                            "is_premium": getattr(chat_member.user, 'is_premium', None),
                            "added_to_attachment_menu": getattr(chat_member.user, 'added_to_attachment_menu', None),
                            "can_join_groups": getattr(chat_member.user, 'can_join_groups', None),
                            "can_read_all_group_messages": getattr(chat_member.user, 'can_read_all_group_messages', None),
                            "supports_inline_queries": getattr(chat_member.user, 'supports_inline_queries', None),
                        }
                    }
                    
                    result["chat_member_info"] = member_dict
                    result["available_methods"].append("get_chat_member")
                    
                except Exception as e:
                    logger.warning(f"获取聊天成员信息失败: {e}")
            
            # 3. 尝试获取聊天管理员列表（仅对群组/频道有效）
            if chat.type in ["group", "supergroup", "channel"]:
                try:
                    logger.info(f"正在获取 chat_id {chat_id} 的管理员列表...")
                    administrators = await self.bot.get_chat_administrators(chat_id)
                    
                    admin_list = []
                    for admin in administrators:
                        admin_dict = {
                            "status": admin.status,
                            "user": {
                                "id": admin.user.id,
                                "is_bot": admin.user.is_bot,
                                "first_name": admin.user.first_name,
                                "last_name": getattr(admin.user, 'last_name', None),
                                "username": getattr(admin.user, 'username', None),
                            },
                            "can_be_edited": getattr(admin, 'can_be_edited', None),
                            "can_manage_chat": getattr(admin, 'can_manage_chat', None),
                            "can_delete_messages": getattr(admin, 'can_delete_messages', None),
                            "can_manage_video_chats": getattr(admin, 'can_manage_video_chats', None),
                            "can_restrict_members": getattr(admin, 'can_restrict_members', None),
                            "can_promote_members": getattr(admin, 'can_promote_members', None),
                            "can_change_info": getattr(admin, 'can_change_info', None),
                            "can_invite_users": getattr(admin, 'can_invite_users', None),
                            "can_post_messages": getattr(admin, 'can_post_messages', None),
                            "can_edit_messages": getattr(admin, 'can_edit_messages', None),
                            "can_pin_messages": getattr(admin, 'can_pin_messages', None),
                            "can_manage_topics": getattr(admin, 'can_manage_topics', None),
                        }
                        admin_list.append(admin_dict)
                    
                    result["administrators"] = admin_list
                    result["available_methods"].append("get_chat_administrators")
                    
                except Exception as e:
                    logger.warning(f"获取管理员列表失败: {e}")
            
            # 4. 尝试获取聊天成员数量
            try:
                logger.info(f"正在获取 chat_id {chat_id} 的成员数量...")
                member_count = await self.bot.get_chat_member_count(chat_id)
                result["member_count"] = member_count
                result["available_methods"].append("get_chat_member_count")
                
            except Exception as e:
                logger.warning(f"获取成员数量失败: {e}")
            
            result["success"] = True
            logger.success(f"成功获取 chat_id {chat_id} 的信息")
            
        except TelegramBadRequest as e:
            result["error"] = f"Bad Request: {e}"
            logger.error(f"获取 chat_id {chat_id} 信息失败 - Bad Request: {e}")
            
        except TelegramForbiddenError as e:
            result["error"] = f"Forbidden: {e}"
            logger.error(f"获取 chat_id {chat_id} 信息失败 - Forbidden: {e}")
            
        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
            logger.error(f"获取 chat_id {chat_id} 信息失败 - Unexpected error: {e}")
        
        return result
    
    async def test_multiple_chats(self, chat_ids: list[int | str]) -> Dict[str, Any]:
        """
        测试多个聊天ID
        
        Args:
            chat_ids: 聊天ID列表
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        results = {}
        
        for chat_id in chat_ids:
            logger.info(f"开始测试 chat_id: {chat_id}")
            result = await self.get_chat_info(chat_id)
            results[str(chat_id)] = result
            
            # 添加延迟避免触发限流
            await asyncio.sleep(1)
        
        return {
            "total_tested": len(chat_ids),
            "successful": sum(1 for r in results.values() if r["success"]),
            "failed": sum(1 for r in results.values() if not r["success"]),
            "results": results
        }
    
    async def get_message_info(self, chat_id: int | str, message_id: int) -> dict:
        """
        获取指定消息的详细信息
        
        参数:
            chat_id: 聊天ID
            message_id: 消息ID
            
        返回:
            包含消息详细信息的字典
        """
        result = {
            "success": False,
            "chat_id": chat_id,
            "message_id": message_id,
            "message_info": None,
            "error": None,
            "available_methods": []
        }
        
        try:
            logger.info(f"正在获取消息信息: chat_id={chat_id}, message_id={message_id}")
            
            # 尝试转发消息来获取消息信息（这是一种获取消息详情的方法）
            try:
                # 注意：这个方法需要bot有转发权限，且目标聊天存在
                message = await self.bot.forward_message(
                    chat_id=chat_id,  # 转发到同一个聊天
                    from_chat_id=chat_id,
                    message_id=message_id,
                    disable_notification=True
                )
                
                # 立即删除转发的消息
                try:
                    await self.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                except Exception:
                    pass  # 忽略删除失败
                
                result["available_methods"].append("forward_message")
                
                # 提取消息信息
                message_data = {
                    "message_id": message.message_id,
                    "from_user": None,
                    "date": message.date.isoformat() if message.date else None,
                    "chat": {
                        "id": message.chat.id,
                        "type": message.chat.type,
                        "title": getattr(message.chat, 'title', None),
                        "username": getattr(message.chat, 'username', None),
                        "first_name": getattr(message.chat, 'first_name', None),
                        "last_name": getattr(message.chat, 'last_name', None),
                    },
                    "content_type": None,
                    "text": getattr(message, 'text', None),
                    "caption": getattr(message, 'caption', None),
                    "entities": [],
                    "caption_entities": [],
                    "media": None,
                    "reply_to_message": None,
                    "forward_info": None,
                    "edit_date": message.edit_date.isoformat() if getattr(message, 'edit_date', None) else None,
                    "media_group_id": getattr(message, 'media_group_id', None),
                    "has_protected_content": getattr(message, 'has_protected_content', False),
                }
                
                # 发送者信息
                if message.from_user:
                    message_data["from_user"] = {
                        "id": message.from_user.id,
                        "is_bot": message.from_user.is_bot,
                        "first_name": message.from_user.first_name,
                        "last_name": getattr(message.from_user, 'last_name', None),
                        "username": getattr(message.from_user, 'username', None),
                        "language_code": getattr(message.from_user, 'language_code', None),
                        "is_premium": getattr(message.from_user, 'is_premium', False),
                    }
                
                # 消息实体（格式化信息）
                if hasattr(message, 'entities') and message.entities:
                    for entity in message.entities:
                        entity_data = {
                            "type": entity.type,
                            "offset": entity.offset,
                            "length": entity.length,
                            "url": getattr(entity, 'url', None),
                            "user": None,
                            "language": getattr(entity, 'language', None),
                        }
                        if hasattr(entity, 'user') and entity.user:
                            entity_data["user"] = {
                                "id": entity.user.id,
                                "first_name": entity.user.first_name,
                                "username": getattr(entity.user, 'username', None),
                            }
                        message_data["entities"].append(entity_data)
                
                # 标题实体
                if hasattr(message, 'caption_entities') and message.caption_entities:
                    for entity in message.caption_entities:
                        entity_data = {
                            "type": entity.type,
                            "offset": entity.offset,
                            "length": entity.length,
                            "url": getattr(entity, 'url', None),
                        }
                        message_data["caption_entities"].append(entity_data)
                
                # 媒体信息
                if hasattr(message, 'photo') and message.photo:
                    message_data["content_type"] = "photo"
                    message_data["media"] = {
                        "type": "photo",
                        "file_id": message.photo[-1].file_id,  # 最大尺寸的照片
                        "file_unique_id": message.photo[-1].file_unique_id,
                        "width": message.photo[-1].width,
                        "height": message.photo[-1].height,
                        "file_size": getattr(message.photo[-1], 'file_size', None),
                    }
                elif hasattr(message, 'video') and message.video:
                    message_data["content_type"] = "video"
                    message_data["media"] = {
                        "type": "video",
                        "file_id": message.video.file_id,
                        "file_unique_id": message.video.file_unique_id,
                        "width": message.video.width,
                        "height": message.video.height,
                        "duration": message.video.duration,
                        "file_size": getattr(message.video, 'file_size', None),
                        "mime_type": getattr(message.video, 'mime_type', None),
                    }
                elif hasattr(message, 'document') and message.document:
                    message_data["content_type"] = "document"
                    message_data["media"] = {
                        "type": "document",
                        "file_id": message.document.file_id,
                        "file_unique_id": message.document.file_unique_id,
                        "file_name": getattr(message.document, 'file_name', None),
                        "mime_type": getattr(message.document, 'mime_type', None),
                        "file_size": getattr(message.document, 'file_size', None),
                    }
                elif hasattr(message, 'audio') and message.audio:
                    message_data["content_type"] = "audio"
                    message_data["media"] = {
                        "type": "audio",
                        "file_id": message.audio.file_id,
                        "file_unique_id": message.audio.file_unique_id,
                        "duration": message.audio.duration,
                        "performer": getattr(message.audio, 'performer', None),
                        "title": getattr(message.audio, 'title', None),
                        "file_size": getattr(message.audio, 'file_size', None),
                        "mime_type": getattr(message.audio, 'mime_type', None),
                    }
                elif hasattr(message, 'voice') and message.voice:
                    message_data["content_type"] = "voice"
                    message_data["media"] = {
                        "type": "voice",
                        "file_id": message.voice.file_id,
                        "file_unique_id": message.voice.file_unique_id,
                        "duration": message.voice.duration,
                        "file_size": getattr(message.voice, 'file_size', None),
                        "mime_type": getattr(message.voice, 'mime_type', None),
                    }
                elif hasattr(message, 'sticker') and message.sticker:
                    message_data["content_type"] = "sticker"
                    message_data["media"] = {
                        "type": "sticker",
                        "file_id": message.sticker.file_id,
                        "file_unique_id": message.sticker.file_unique_id,
                        "width": message.sticker.width,
                        "height": message.sticker.height,
                        "is_animated": message.sticker.is_animated,
                        "is_video": getattr(message.sticker, 'is_video', False),
                        "emoji": getattr(message.sticker, 'emoji', None),
                        "set_name": getattr(message.sticker, 'set_name', None),
                    }
                elif message.text:
                    message_data["content_type"] = "text"
                
                # 回复信息
                if hasattr(message, 'reply_to_message') and message.reply_to_message:
                    reply_msg = message.reply_to_message
                    message_data["reply_to_message"] = {
                        "message_id": reply_msg.message_id,
                        "from_user_id": reply_msg.from_user.id if reply_msg.from_user else None,
                        "date": reply_msg.date.isoformat() if reply_msg.date else None,
                        "text": getattr(reply_msg, 'text', None),
                        "caption": getattr(reply_msg, 'caption', None),
                    }
                
                # 转发信息
                if hasattr(message, 'forward_from') and message.forward_from:
                    message_data["forward_info"] = {
                        "type": "user",
                        "from_user": {
                            "id": message.forward_from.id,
                            "first_name": message.forward_from.first_name,
                            "username": getattr(message.forward_from, 'username', None),
                        },
                        "date": message.forward_date.isoformat() if hasattr(message, 'forward_date') and message.forward_date else None,
                    }
                elif hasattr(message, 'forward_from_chat') and message.forward_from_chat:
                    message_data["forward_info"] = {
                        "type": "chat",
                        "from_chat": {
                            "id": message.forward_from_chat.id,
                            "type": message.forward_from_chat.type,
                            "title": getattr(message.forward_from_chat, 'title', None),
                            "username": getattr(message.forward_from_chat, 'username', None),
                        },
                        "date": message.forward_date.isoformat() if hasattr(message, 'forward_date') and message.forward_date else None,
                        "message_id": getattr(message, 'forward_from_message_id', None),
                    }
                
                result["message_info"] = message_data
                result["success"] = True
                
            except TelegramBadRequest as e:
                if "message to forward not found" in str(e).lower():
                    result["error"] = f"消息不存在或已被删除 (message_id: {message_id})"
                elif "not enough rights" in str(e).lower():
                    result["error"] = "权限不足，无法访问该消息"
                elif "chat not found" in str(e).lower():
                    result["error"] = f"聊天不存在 (chat_id: {chat_id})"
                else:
                    result["error"] = f"无法获取消息: {str(e)}"
                logger.warning(f"获取消息 {message_id} 失败: {e}")
                
            except TelegramForbiddenError as e:
                result["error"] = f"权限被拒绝: {str(e)}"
                logger.warning(f"获取消息 {message_id} 权限被拒绝: {e}")
                
        except Exception as e:
            result["error"] = f"获取消息信息时发生错误: {str(e)}"
            logger.error(f"获取消息信息异常: {e}")
        
        return result

    async def close(self):
        """关闭Bot会话"""
        await self.bot.session.close()


async def main():
    """主测试函数"""
    tester = ChatInfoTester()
    
    try:
        # 测试示例chat_ids（你可以替换为实际的chat_id）
        test_chat_ids = [
            # 添加你想测试的chat_id
            # 例如: 123456789, "@username", -1001234567890
        ]
        
        # 测试消息信息（可选）
        test_messages = [
            # 添加你想测试的消息，格式: (chat_id, message_id)
            # 例如: (123456789, 1), (-1001234567890, 100)
        ]
        
        # 测试消息信息（可选）
        test_messages = [
            # 添加你想测试的消息，格式: (chat_id, message_id)
            # 例如: (123456789, 1), (-1001234567890, 100)
        ]
        
        if not test_chat_ids and not test_messages:
            logger.warning("没有提供测试的chat_id或消息，请在test_chat_ids或test_messages列表中添加要测试的内容")
            return
        
        # 执行聊天信息测试
        if test_chat_ids:
            logger.info("开始测试聊天信息...")
            chat_results = await tester.test_multiple_chats(test_chat_ids)
            
            # 输出聊天信息结果
            print("\n" + "="*50)
            print("Chat ID 信息测试结果")
            print("="*50)
            print(json.dumps(chat_results, indent=2, ensure_ascii=False))
        
        # 执行消息信息测试
        if test_messages:
            logger.info("开始测试消息信息...")
            message_results = {}
            
            for chat_id, message_id in test_messages:
                logger.info(f"测试消息: chat_id={chat_id}, message_id={message_id}")
                result = await tester.get_message_info(chat_id, message_id)
                message_results[f"{chat_id}_{message_id}"] = result
                
                # 添加延迟避免触发限流
                await asyncio.sleep(1)
            
            # 输出消息信息结果
            print("\n" + "="*50)
            print("消息信息测试结果")
            print("="*50)
            print(json.dumps({
                "total_tested": len(test_messages),
                "successful": sum(1 for r in message_results.values() if r["success"]),
                "failed": sum(1 for r in message_results.values() if not r["success"]),
                "results": message_results
            }, indent=2, ensure_ascii=False))
        
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())