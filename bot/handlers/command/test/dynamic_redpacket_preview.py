from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message
from loguru import logger

from bot.services.redpacket_preview import compose_redpacket_with_info

router = Router(name="test_dynamic_redpacket_preview")


@router.message(Command("test_rp"))
async def test_dynamic_redpacket_preview(message: Message, command: CommandObject) -> None:
    args_raw = (command.args or "").strip()
    parts = args_raw.split() if args_raw else []

    sender_name = "测试用户"
    amount = 100.0
    count = 5

    if parts:
        if len(parts) not in (2, 3):
            await message.reply("用法: /test_rp 用户名 金额 [份数]", parse_mode=None)
            return
        sender_name = parts[0]
        try:
            amount = float(parts[1])
        except ValueError:
            await message.reply("金额必须是数字", parse_mode=None)
            return
        if len(parts) == 3:
            try:
                count = int(parts[2])
            except ValueError:
                await message.reply("份数必须是整数", parse_mode=None)
                return

    try:
        path = compose_redpacket_with_info(
            cover_name=None,
            body_name=None,
            sender_name=sender_name,
            message="恭喜发财，大吉大利",
            amount=amount,
            count=count,
            watermark_text="WeChat Team",
            watermark_image_name=None,
            avatar_image_name="sakura.png",
        )
    except Exception:
        logger.exception("生成红包模板预览失败: sender=%s amount=%s count=%s", sender_name, amount, count)
        await message.reply("生成预览失败，请检查日志", parse_mode=None)
        return

    try:
        file = FSInputFile(path)
        await message.answer_photo(
            photo=file,
            caption=f"测试红包模板预览\n发红包: {sender_name}\n金额: {amount} 💧 / {count}",
        )
    except Exception:
        logger.exception("发送红包模板预览失败: path=%s", path)
        await message.reply("发送预览失败，请检查日志", parse_mode=None)
