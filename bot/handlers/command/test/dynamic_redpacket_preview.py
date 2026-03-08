from __future__ import annotations

import time
import asyncio
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from bot.services.redpacket_preview import compose_redpacket_with_info
from bot.utils.text import escape_markdown_v2

router = Router(name="test_dynamic_redpacket_preview")

# 简单的内存缓存，存储 {file_unique_id: bytes}
# 注意：在生产环境中应考虑过期时间和内存占用，这里仅作为演示优化
AVATAR_CACHE: dict[str, bytes] = {}

@router.message(Command("test_rp"))
async def test_dynamic_redpacket_preview(message: Message, command: CommandObject) -> None:
    # 立即发送状态提示，减少等待焦虑
    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
    start_total = time.time()
    args_raw = (command.args or "").strip()
    parts = args_raw.split() if args_raw else []

    # 默认使用发送者名字
    sender_name = message.from_user.first_name if message.from_user else "测试用户"
    amount = 100
    count = 5
    
    # 获取用户头像
    avatar_content = None
    if message.from_user:
        try:
            t0 = time.time()
            user_photos = await message.from_user.get_profile_photos(limit=1)
            logger.info(f"获取用户头像元数据耗时: {time.time() - t0:.4f}s")
            
            if user_photos.total_count > 0:
                # 优先使用高清大图 (-1: big)，保证预览质量
                photo = user_photos.photos[0][-1] 
                
                # 检查内存缓存
                if photo.file_unique_id in AVATAR_CACHE:
                    avatar_content = AVATAR_CACHE[photo.file_unique_id]
                    logger.info("命中头像内存缓存，跳过下载")
                else:
                    t1 = time.time()
                    file = await message.bot.get_file(photo.file_id)
                    logger.info(f"获取头像文件路径耗时: {time.time() - t1:.4f}s")
                    
                    # 下载头像内容
                    import io
                    avatar_io = io.BytesIO()
                    t2 = time.time()
                    await message.bot.download_file(file.file_path, avatar_io)
                    logger.info(f"下载头像耗时: {time.time() - t2:.4f}s")
                    avatar_content = avatar_io.getvalue()
                    
                    # 写入缓存
                    AVATAR_CACHE[photo.file_unique_id] = avatar_content
                    # 简单限制缓存大小防止溢出
                    if len(AVATAR_CACHE) > 100:
                        AVATAR_CACHE.clear()
        except Exception as e:
            logger.warning(f"获取用户头像失败: {e}")

    # 如果有参数，尝试解析
    if parts:
        try:
            amount = float(parts[0])
            if len(parts) > 1:
                try:
                    count = int(parts[1])
                except ValueError:
                    pass
        except ValueError:
            sender_name = parts[0]
            if len(parts) > 1:
                try:
                    amount = float(parts[1])
                except ValueError:
                    pass
            if len(parts) > 2:
                try:
                    count = int(parts[2])
                except ValueError:
                    pass

    try:
        t3 = time.time()
        # 使用 run_in_executor 避免阻塞事件循环
        loop = asyncio.get_running_loop()
        # 修改为返回字节流，避免磁盘 I/O
        img_bytes, filename = await loop.run_in_executor(
            None, 
            lambda: compose_redpacket_with_info(
                cover_name=None,  # 随机
                body_name=None,   # 随机
                sender_name=sender_name,
                amount=amount,
                count=count,
                group_text=None,
                watermark_image_name=None,
                avatar_image_name=None,
                avatar_file_content=avatar_content,
                return_bytes=True,
            )
        )
        logger.info(f"生成最终图片耗时: {time.time() - t3:.4f}s")
    except Exception:
        logger.exception("生成红包模板预览失败: sender=%s amount=%s count=%s", sender_name, amount, count)
        await message.reply("生成预览失败，请检查日志", parse_mode=None)
        return

    # 构建生动的按钮
    kb = InlineKeyboardBuilder()
    kb.button(text="🧧 抢红包", callback_data="test_rp_click")
    
    try:
        t4 = time.time()
        logger.info(f"图片大小: {len(img_bytes) / 1024:.2f} KB")
        # 使用 BufferedInputFile 直接发送内存中的图片数据
        file = BufferedInputFile(img_bytes, filename=filename)
        escaped_name = escape_markdown_v2(sender_name)
        final_caption = f"🧧 *{escaped_name}* 发出一个拼手气红包\n\n恭喜发财，大吉大利"

        await message.answer_photo(
            photo=file,
            caption=final_caption,
            parse_mode="MarkdownV2",
            reply_markup=kb.as_markup()
        )
        logger.info(f"发送图片耗时: {time.time() - t4:.4f}s")
    except Exception:
        logger.exception("发送红包模板预览失败")
        await message.reply("发送预览失败，请检查日志", parse_mode=None)
    
    logger.info(f"总耗时: {time.time() - start_total:.4f}s")


@router.callback_query(F.data == "test_rp_click")
async def on_test_rp_click(callback: CallbackQuery):
    await callback.answer("🎉 恭喜！这是一个测试红包，你抢到了 0.00 元！", show_alert=True)
