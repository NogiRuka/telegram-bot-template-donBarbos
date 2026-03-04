from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from bot.services.redpacket_preview import compose_redpacket_with_info
from bot.utils.text import escape_markdown_v2

router = Router(name="test_dynamic_redpacket_preview")


@router.message(Command("test_rp"))
async def test_dynamic_redpacket_preview(message: Message, command: CommandObject) -> None:
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
            user_photos = await message.from_user.get_profile_photos(limit=1)
            if user_photos.total_count > 0:
                # 获取最大尺寸
                photo = user_photos.photos[0][-1]
                file = await message.bot.get_file(photo.file_id)
                # 下载头像内容
                import io
                avatar_io = io.BytesIO()
                await message.bot.download_file(file.file_path, avatar_io)
                avatar_content = avatar_io.getvalue()
        except Exception as e:
            logger.warning(f"获取用户头像失败: {e}")

    # 如果有参数，尝试解析
    if parts:
        # 如果第一个参数看起来像数字，则认为是金额，保持 sender_name 为发送者
        # 如果第一个参数不是数字，则认为是指定的发送者名字
        try:
            amount = float(parts[0])
            # 如果成功解析了金额，看后面有没有份数
            if len(parts) > 1:
                try:
                    count = int(parts[1])
                except ValueError:
                    pass # 忽略错误的份数
        except ValueError:
            # 第一个参数不是数字，当作名字
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
        path = compose_redpacket_with_info(
            cover_name=None,
            body_name=None,
            sender_name=sender_name,
            amount=amount,
            count=count,
            group_text=None,
            watermark_image_name=None,
            avatar_image_name=None,
            avatar_file_content=avatar_content,
        )
    except Exception:
        logger.exception("生成红包模板预览失败: sender=%s amount=%s count=%s", sender_name, amount, count)
        await message.reply("生成预览失败，请检查日志", parse_mode=None)
        return

    # 构建生动的按钮
    kb = InlineKeyboardBuilder()
    kb.button(text="🧧 抢红包", callback_data="test_rp_click")
    
    try:
        file = FSInputFile(path)
        escaped_name = escape_markdown_v2(sender_name)
        await message.answer_photo(
            photo=file,
            caption=f"🧧 *{escaped_name}* 发出一个拼手气红包\n\n恭喜发财，大吉大利",
            parse_mode="MarkdownV2",
            reply_markup=kb.as_markup()
        )
    except Exception:
        logger.exception("发送红包模板预览失败: path=%s", path)
        await message.reply("发送预览失败，请检查日志", parse_mode=None)


@router.callback_query(F.data == "test_rp_click")
async def on_test_rp_click(callback: CallbackQuery):
    await callback.answer("🎉 恭喜！这是一个测试红包，你抢到了 0.00 元！", show_alert=True)
