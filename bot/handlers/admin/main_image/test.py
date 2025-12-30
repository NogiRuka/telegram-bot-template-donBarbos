import contextlib

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .router import router
from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.keyboards.inline.admin import get_main_image_back_keyboard, get_main_image_cancel_keyboard
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.admin import AdminMainImageState
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2, format_size


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":test")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_test(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始图片测试工具

    功能说明:
    - 引导输入 file_id 或发送图片进行信息回显

    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    await state.set_state(AdminMainImageState.waiting_for_test_input)
    await main_msg.update_on_callback(
        callback,
        escape_markdown_v2("请发送图片或直接输入 Telegram file_id："),
        get_main_image_cancel_keyboard()
    )
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_test_input)
async def process_test_input(message: Message, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理测试输入"""
    with contextlib.suppress(Exception):
        await main_msg.delete_input(message)
    file_id: str | None = None
    caption_lines: list[str] = ["*🧪 图片测试结果*"]
    if message.photo:
        p = message.photo[-1]
        file_id = p.file_id
        caption_lines.extend([
            "类型: Photo",
            f"尺寸: {p.width}x{p.height}",
            f"大小: {format_size(p.file_size)}",
        ])
    elif message.document:
        doc = message.document
        file_id = doc.file_id
        caption_lines.extend([
            f"类型: Document ({doc.mime_type or '-'})",
            f"大小: {format_size(doc.file_size)}",
        ])
    else:
        file_id = message.text.strip()
        caption_lines.append("类型: file_id")

    safe_lines = [caption_lines[0]] + [escape_markdown_v2(line) for line in caption_lines[1:]]
    safe_caption = "\n".join(safe_lines)

    try:
        await message.bot.send_photo(chat_id=message.chat.id, photo=file_id, caption=safe_caption, parse_mode="MarkdownV2")
        # 测试成功后，更新主消息提示已完成，或保持等待状态?
        # 原逻辑清除状态。这里改为显示返回键盘。
        await main_msg.render(message.from_user.id, "✅ 测试消息已发送。", get_main_image_back_keyboard())
    except Exception as e:
        await message.answer(f"❌ 发送失败，请确认 file_id 有效或重试。\n错误: {e}")

    await state.clear()
