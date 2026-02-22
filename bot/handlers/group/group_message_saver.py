"""
群组消息保存处理器模块

本模块实现了自动保存群组消息的功能，
根据群组配置自动保存符合条件的消息到数据库。
"""

import json
from typing import Any

from aiogram import F, Router, types
from aiogram.enums import ChatMemberStatus, ChatType
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    GroupConfigModel,
    GroupType,
    MessageModel,
    MessageSaveMode,
    MessageType,
)
from bot.services.group_config_service import get_or_create_group_config

router = Router()


class GroupMessageSaver:
    """群组消息保存器类"""

    def __init__(self) -> None:
        self.message_type_mapping = {
            "text": MessageType.TEXT,
            "photo": MessageType.PHOTO,
            "video": MessageType.VIDEO,
            "audio": MessageType.AUDIO,
            "voice": MessageType.VOICE,
            "document": MessageType.DOCUMENT,
            "sticker": MessageType.STICKER,
            "animation": MessageType.ANIMATION,
            "location": MessageType.LOCATION,
            "contact": MessageType.CONTACT,
            "poll": MessageType.POLL,
            "dice": MessageType.DICE,
            "game": MessageType.GAME,
            "invoice": MessageType.INVOICE,
            "successful_payment": MessageType.SUCCESSFUL_PAYMENT,
            "video_note": MessageType.VIDEO_NOTE,
            "venue": MessageType.VENUE,
            "web_app_data": MessageType.WEB_APP_DATA,
        }

    async def get_group_config(self, chat_id: int, session: AsyncSession) -> GroupConfigModel | None:
        try:
            result = await session.execute(
                select(GroupConfigModel).where(
                    GroupConfigModel.chat_id == chat_id,
                    GroupConfigModel.is_deleted.is_(False),
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"❌ 获取群组配置失败: {e}")
            return None

    async def create_default_config(self, chat: types.Chat, session: AsyncSession) -> GroupConfigModel | None:
        try:
            if chat.type == "group":
                group_type = GroupType.GROUP
            elif chat.type == "supergroup":
                group_type = GroupType.SUPERGROUP
            elif chat.type == "channel":
                group_type = GroupType.CHANNEL
            else:
                logger.warning(f"⚠️ 未知的聊天类型: {chat.type}")
                return None

            config = GroupConfigModel.create_for_group(
                chat_id=chat.id,
                chat_title=chat.title,
                chat_username=chat.username,
                group_type=group_type,
                is_message_save_enabled=False,
                message_save_mode=MessageSaveMode.DISABLED,
            )

            session.add(config)
            await session.commit()
            logger.info(f"✅ 为群组 {chat.id} 创建了默认配置")
            return config
        except Exception as e:
            logger.exception(f"❌ 创建群组默认配置失败: {e}")
            await session.rollback()
            return None

    def get_message_type(self, message: types.Message) -> MessageType:
        if message.photo:
            return MessageType.PHOTO
        if message.video:
            return MessageType.VIDEO
        if message.audio:
            return MessageType.AUDIO
        if message.voice:
            return MessageType.VOICE
        if message.document:
            return MessageType.DOCUMENT
        if message.sticker:
            return MessageType.STICKER
        if message.animation:
            return MessageType.ANIMATION
        if message.location:
            return MessageType.LOCATION
        if message.contact:
            return MessageType.CONTACT
        if message.poll:
            return MessageType.POLL
        if message.dice:
            return MessageType.DICE
        if message.game:
            return MessageType.GAME
        if message.invoice:
            return MessageType.INVOICE
        if message.successful_payment:
            return MessageType.SUCCESSFUL_PAYMENT
        if message.video_note:
            return MessageType.VIDEO_NOTE
        if message.venue:
            return MessageType.VENUE
        if message.web_app_data:
            return MessageType.WEB_APP_DATA
        if message.text:
            return MessageType.TEXT
        return MessageType.OTHER

    def extract_file_info(self, message: types.Message) -> dict[str, Any]:
        file_info = {
            "file_id": None,
            "file_unique_id": None,
            "file_size": None,
            "file_name": None,
            "mime_type": None,
        }
        if message.photo:
            largest_photo = max(message.photo, key=lambda x: x.file_size or 0)
            file_info.update(
                {
                    "file_id": largest_photo.file_id,
                    "file_unique_id": largest_photo.file_unique_id,
                    "file_size": largest_photo.file_size,
                }
            )
        elif message.video:
            file_info.update(
                {
                    "file_id": message.video.file_id,
                    "file_unique_id": message.video.file_unique_id,
                    "file_size": message.video.file_size,
                    "file_name": message.video.file_name,
                    "mime_type": message.video.mime_type,
                }
            )
        elif message.audio:
            file_info.update(
                {
                    "file_id": message.audio.file_id,
                    "file_unique_id": message.audio.file_unique_id,
                    "file_size": message.audio.file_size,
                    "file_name": message.audio.file_name,
                    "mime_type": message.audio.mime_type,
                }
            )
        elif message.voice:
            file_info.update(
                {
                    "file_id": message.voice.file_id,
                    "file_unique_id": message.voice.file_unique_id,
                    "file_size": message.voice.file_size,
                    "mime_type": message.voice.mime_type,
                }
            )
        elif message.document:
            file_info.update(
                {
                    "file_id": message.document.file_id,
                    "file_unique_id": message.document.file_unique_id,
                    "file_size": message.document.file_size,
                    "file_name": message.document.file_name,
                    "mime_type": message.document.mime_type,
                }
            )
        elif message.sticker:
            file_info.update(
                {
                    "file_id": message.sticker.file_id,
                    "file_unique_id": message.sticker.file_unique_id,
                    "file_size": message.sticker.file_size,
                }
            )
        elif message.animation:
            file_info.update(
                {
                    "file_id": message.animation.file_id,
                    "file_unique_id": message.animation.file_unique_id,
                    "file_size": message.animation.file_size,
                    "file_name": message.animation.file_name,
                    "mime_type": message.animation.mime_type,
                }
            )
        elif message.video_note:
            file_info.update(
                {
                    "file_id": message.video_note.file_id,
                    "file_unique_id": message.video_note.file_unique_id,
                    "file_size": message.video_note.file_size,
                }
            )
        return file_info

    def check_keywords(self, text: str, include_keywords: str | None, exclude_keywords: str | None) -> bool:
        if not text:
            return True
        text_lower = text.lower()
        if include_keywords:
            try:
                keywords = json.loads(include_keywords)
                if keywords and not any(keyword.lower() in text_lower for keyword in keywords):
                    return False
            except json.JSONDecodeError:
                logger.warning(f"❌ 包含关键词配置格式错误: {include_keywords}")
        if exclude_keywords:
            try:
                keywords = json.loads(exclude_keywords)
                if keywords and any(keyword.lower() in text_lower for keyword in keywords):
                    return False
            except json.JSONDecodeError:
                logger.warning(f"❌ 排除关键词配置格式错误: {exclude_keywords}")
        return True

    def generate_service_message_text(self, message: types.Message) -> str | None:
        """生成系统服务消息的文本描述"""
        if message.new_chat_members:
            names = [f"{u.full_name}" for u in message.new_chat_members]
            # 检查是自己加入还是被邀请
            if message.from_user and len(message.new_chat_members) == 1 and message.from_user.id == message.new_chat_members[0].id:
                return f"{message.from_user.full_name} 加入了群组"
            if message.from_user:
                 return f"{message.from_user.full_name} 添加了成员: {', '.join(names)}"
            return f"添加了成员: {', '.join(names)}"
        if message.left_chat_member:
            if message.from_user and message.from_user.id != message.left_chat_member.id:
                return f"{message.from_user.full_name} 移除了成员: {message.left_chat_member.full_name}"
            return f"成员离开: {message.left_chat_member.full_name}"
        if message.new_chat_title:
            return f"群组名称修改为: {message.new_chat_title}"
        if message.new_chat_photo:
            return "群组头像已修改"
        if message.delete_chat_photo:
            return "群组头像已移除"
        if message.group_chat_created:
            return "群组已创建"
        if message.supergroup_chat_created:
            return "超级群组已创建"
        if message.channel_chat_created:
            return "频道已创建"
        if message.message_auto_delete_timer_changed:
            time = message.message_auto_delete_timer_changed.message_auto_delete_time
            if time == 0:
                return "自动删除已禁用"
            if time < 60:
                time_str = f"{time} 秒"
            elif time < 3600:
                time_str = f"{time // 60} 分钟"
            elif time < 86400:
                time_str = f"{time // 3600} 小时"
            else:
                time_str = f"{time // 86400} 天"
            return f"您将消息设置为在 {time_str} 内自动删除"
        if message.pinned_message:
            return "置顶了一条消息"
        if message.migrate_to_chat_id:
            return f"群组升级为超级群组，新ID: {message.migrate_to_chat_id}"
        if message.migrate_from_chat_id:
            return f"群组由普通群组升级而来，原ID: {message.migrate_from_chat_id}"
        if message.successful_payment:
            return f"支付成功: {message.successful_payment.total_amount / 100} {message.successful_payment.currency}"
        if message.connected_website:
            return f"登录网站: {message.connected_website}"
        if message.write_access_allowed:
            return "允许写入访问"
        if message.passport_data:
            return "收到护照数据"
        if message.proximity_alert_triggered:
            user = message.proximity_alert_triggered.traveler
            dist = message.proximity_alert_triggered.distance
            return f"接近警报: {user.full_name} 距离 {dist} 米"
        if message.video_chat_scheduled:
            return f"视频聊天已安排: {message.video_chat_scheduled.start_date}"
        if message.video_chat_started:
            return "视频聊天已开始"
        if message.video_chat_ended:
            duration = message.video_chat_ended.duration
            return f"视频聊天已结束，持续 {duration} 秒"
        if message.video_chat_participants_invited:
            users = [u.full_name for u in message.video_chat_participants_invited.users]
            return f"邀请加入视频聊天: {', '.join(users)}"
        if message.forum_topic_created:
            return f"创建了话题: {message.forum_topic_created.name}"
        if message.forum_topic_edited:
            return f"编辑了话题: {message.forum_topic_edited.name or '图标'}"
        if message.forum_topic_closed:
            return "关闭了话题"
        if message.forum_topic_reopened:
            return "重新打开了话题"
        if message.general_forum_topic_hidden:
            return "隐藏了通用话题"
        if message.general_forum_topic_unhidden:
            return "取消隐藏通用话题"
        return None

    def extract_entities(self, entities: list | None) -> str | None:
        if not entities:
            return None
        try:
            entities_data = []
            for entity in entities:
                entity_dict = {
                    "type": entity.type,
                    "offset": entity.offset,
                    "length": entity.length,
                }
                if entity.type in {"url", "text_link"}:
                    entity_dict["url"] = entity.url if hasattr(entity, "url") else None
                elif entity.type == "text_mention":
                    if hasattr(entity, "user") and entity.user:
                        entity_dict["user"] = {
                            "id": entity.user.id,
                            "first_name": entity.user.first_name,
                            "last_name": entity.user.last_name,
                            "username": entity.user.username,
                        }
                elif (
                    entity.type
                    in [
                        "bold",
                        "italic",
                        "underline",
                        "strikethrough",
                        "spoiler",
                        "code",
                        "pre",
                    ]
                    and entity.type == "pre"
                    and hasattr(entity, "language")
                ):
                    entity_dict["language"] = entity.language
                entities_data.append(entity_dict)
            return json.dumps(entities_data, ensure_ascii=False) if entities_data else None
        except Exception as e:
            logger.exception(f"❌ 提取实体信息失败: {e}")
            return None

    async def save_message(self, message: types.Message, config: GroupConfigModel, session: AsyncSession) -> bool:
        try:
            message_type = self.get_message_type(message)
            is_forwarded = message.forward_from is not None or message.forward_from_chat is not None
            is_reply = message.reply_to_message is not None

            # 预处理文本内容，检查是否为服务消息
            text_content = message.text or message.caption or ""
            is_service_message = False
            if not text_content:
                service_text = self.generate_service_message_text(message)
                if service_text:
                    text_content = service_text
                    is_service_message = True
                    if message_type == MessageType.OTHER:
                        message_type = MessageType.TEXT

            is_admin_notification = False
            is_from_bot = message.from_user and message.from_user.is_bot and not is_service_message and not is_admin_notification

            if not config.should_save_message(
                message_type=message_type.value,
                is_forwarded=is_forwarded,
                is_reply=is_reply,
                is_from_bot=is_from_bot,
            ):
                return False

            if not self.check_keywords(text_content, config.include_keywords, config.exclude_keywords):
                return False
            file_info = self.extract_file_info(message)
            if (
                config.max_file_size_mb
                and file_info["file_size"]
                and file_info["file_size"] > config.max_file_size_mb * 1024 * 1024
            ):
                logger.info(f"ℹ️ 消息 {message.message_id} 文件大小超过限制，跳过保存")
                return False
            entities_json = self.extract_entities(message.entities) if message.entities else None
            caption_entities_json = (
                self.extract_entities(message.caption_entities) if message.caption_entities else None
            )
            message_record = MessageModel.create_from_telegram(
                message_id=message.message_id,
                user_id=message.from_user.id if message.from_user else 0,
                chat_id=message.chat.id,
                message_type=message_type,
                text_content=text_content[:1000] if text_content else None,
                caption=message.caption[:1000] if message.caption else None,
                entities=entities_json,
                caption_entities=caption_entities_json,
                file_id=file_info["file_id"],
                file_unique_id=file_info["file_unique_id"],
                file_size=file_info["file_size"],
                file_name=file_info["file_name"],
                mime_type=file_info["mime_type"],
                is_forwarded=is_forwarded,
                is_reply=is_reply,
            )
            if is_forwarded:
                if message.forward_from:
                    message_record.forward_from_user_id = message.forward_from.id
                elif message.forward_from_chat:
                    message_record.forward_from_chat_id = message.forward_from_chat.id
                if hasattr(message, "forward_from_message_id"):
                    message_record.forward_from_message_id = message.forward_from_message_id
            if is_reply and message.reply_to_message:
                message_record.reply_to_message_id = message.reply_to_message.message_id
                if message.reply_to_message.from_user:
                    message_record.reply_to_user_id = message.reply_to_message.from_user.id
            session.add(message_record)
            config.increment_message_count(message_record.created_at)
            await session.commit()
            logger.info(
                f"✅ 成功保存消息: 群组={message.chat.id}, 消息ID={message.message_id}, 类型={message_type.value}"
            )
            return True
        except Exception as e:
            logger.exception(f"❌ 保存消息失败: {e}")
            await session.rollback()
            return False

    async def save_chat_member_event(self, event: types.ChatMemberUpdated, config: GroupConfigModel, session: AsyncSession) -> bool:

        try:
            # 先看看 event 里有什么
            logger.info(f"👥 ChatMemberUpdated 事件: {event}")
            text_content = None
            old = event.old_chat_member
            new = event.new_chat_member

            if new.status == ChatMemberStatus.MEMBER and old.status in {
                ChatMemberStatus.LEFT,
                ChatMemberStatus.KICKED,
            }:
                actor = event.from_user
                member = new.user
                if actor and actor.id != member.id:
                    text_content = f"👋 {actor.full_name} 邀请加入群组: {member.full_name}"
                else:
                    text_content = f"👋 成员加入: {member.full_name}"

            if not text_content and not event.from_user.is_bot:
                return False

            # 成员被移除/封禁
            if new.status in {ChatMemberStatus.KICKED, ChatMemberStatus.LEFT} and old.status in {
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.RESTRICTED,
            }:
                action = "永久封禁" if new.status == "kicked" else "移除"
                text_content = f"🚫 {event.from_user.full_name} {action}了成员: {new.user.full_name}"

            # 成员权限变更（禁言等）
            elif new.status == ChatMemberStatus.RESTRICTED and old.status in {
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
            }:
                text_content = f"🔇 {event.from_user.full_name} 限制了成员: {new.user.full_name}"

            # 成员被提升为管理员
            elif new.status == ChatMemberStatus.ADMINISTRATOR and old.status != ChatMemberStatus.ADMINISTRATOR:
                 text_content = f"🛡 {event.from_user.full_name} 将成员提升为管理员: {new.user.full_name}"

            if not text_content:
                return False

            # 使用负数时间戳作为虚拟消息ID，确保唯一性
            import time
            virtual_message_id = -int(time.time() * 1000000)

            message_record = MessageModel.create_from_telegram(
                message_id=virtual_message_id,
                user_id=event.from_user.id,
                chat_id=event.chat.id,
                message_type=MessageType.OTHER,
                text_content=text_content,
                caption=None,
                entities=None,
                caption_entities=None,
                file_id=None,
                file_unique_id=None,
                file_size=None,
                file_name=None,
                mime_type=None,
                is_forwarded=False,
                is_reply=False,
            )

            session.add(message_record)
            config.increment_message_count(message_record.created_at)
            await session.commit()
            logger.info(
                f"✅ 成功保存事件消息: 群组={event.chat.id}, 虚拟ID={virtual_message_id}, 内容={text_content}"
            )
            return True
        except Exception as e:
            logger.exception(f"❌ 保存事件消息失败: {e}")
            await session.rollback()
            return False


message_saver = GroupMessageSaver()


@router.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]))
async def handle_group_message(message: types.Message, session: AsyncSession) -> None:
    try:
        if message.new_chat_members:
            logger.info(
                f"ℹ️ 入群服务消息由 member_events 处理保存，跳过通用保存: "
                f"chat={message.chat.id}, message_id={message.message_id}"
            )
            return
        logger.info(f"💬 收到群组消息: chat={message.chat.id}, text={message.text}")
        group_type = GroupType.SUPERGROUP if message.chat.type == "supergroup" else GroupType.GROUP
        config = await get_or_create_group_config(
            session=session,
            chat_id=message.chat.id,
            chat_title=message.chat.title,
            chat_username=message.chat.username,
            group_type=group_type,
            configured_by_user_id=message.from_user.id if message.from_user else 0,
        )
        if config.is_save_enabled():
            success = await message_saver.save_message(message, config, session)
            if success:
                logger.info(f"✅ 群组 {message.chat.id} 的消息已保存")
        else:
            logger.info(f"ℹ️ 群组 {message.chat.id} 未启用消息保存 (Mode: {config.message_save_mode})")
    except Exception as e:
        logger.exception(f"❌ 处理群组消息时发生错误: {e}")


@router.chat_member(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]))
async def handle_chat_member_update(event: types.ChatMemberUpdated, session: AsyncSession) -> None:
    try:
        # 获取群组配置
        result = await session.execute(
            select(GroupConfigModel).where(
                GroupConfigModel.chat_id == event.chat.id,
                GroupConfigModel.is_deleted.is_(False),
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            logger.info(f"ℹ️ 未找到群组配置，跳过成员事件保存: chat={event.chat.id}")
            return

        if not config.is_save_enabled():
            logger.info(f"ℹ️ 群组未启用消息保存，跳过成员事件保存: chat={event.chat.id}")
            return

        # 尝试保存事件
        await message_saver.save_chat_member_event(event, config, session)

    except Exception as e:
        logger.exception(f"❌ 处理成员变更事件时发生错误: {e}")


@router.edited_message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]))
async def handle_edited_group_message(message: types.Message, session: AsyncSession) -> None:
    try:
        result = await session.execute(
            select(MessageModel).where(
                MessageModel.message_id == message.message_id,
                MessageModel.chat_id == message.chat.id,
                MessageModel.is_deleted.is_(False),
            )
        )
        existing_message = result.scalar_one_or_none()
        if existing_message:
            existing_message.text_content = (message.text or message.caption or "")[:1000]
            existing_message.caption = message.caption[:1000] if message.caption else None
            existing_message.mark_as_edited(message.edit_date)
            await session.commit()
            logger.info(f"✅ 更新了编辑消息: 群组={message.chat.id}, 消息ID={message.message_id}")
    except Exception as e:
        logger.exception(f"❌ 处理编辑消息时发生错误: {e}")
        await session.rollback()


__all__ = ["GroupMessageSaver", "message_saver", "router"]
