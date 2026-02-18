from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message
from loguru import logger

from bot.services.redpacket_preview import generate_dynamic_redpacket_preview

router = Router(name="test_dynamic_redpacket_preview")


@router.message(Command("test_rp"))
async def test_dynamic_redpacket_preview(message: Message, command: CommandObject) -> None:
    args_raw = (command.args or "").strip()
    parts = args_raw.split() if args_raw else []
    if len(parts) != 2:
        await message.reply("用法: /test_rp 用户名 金额", parse_mode=None)
        return
    name, amount = parts
    try:
        path = generate_dynamic_redpacket_preview(name=name, amount=amount)
    except Exception:
        logger.exception("生成红包封面预览失败: name=%s amount=%s", name, amount)
        await message.reply("生成预览失败，请检查日志", parse_mode=None)
        return
    try:
        file = FSInputFile(path)
        await message.answer_photo(photo=file, caption=f"测试红包封面预览\n用户: {name}\n金额: {amount}")
    except Exception:
        logger.exception("发送红包封面预览失败: name=%s amount=%s path=%s", name, amount, path)
        await message.reply("发送预览失败，请检查日志", parse_mode=None)
