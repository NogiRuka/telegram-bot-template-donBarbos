from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.database.models import MainImageModel
from bot.keyboards.inline.admin import (
    get_main_image_cancel_keyboard, 
    get_main_image_back_keyboard,
    get_main_image_upload_type_keyboard,
    get_main_image_upload_success_keyboard
)
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.admin import AdminMainImageState
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2
from .router import router

@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_upload_selection(callback: CallbackQuery, main_msg: MainMessageService) -> None:
    """开始上传流程 - 选择类型
    
    功能说明:
    - 显示 SFW/NSFW 选择键盘
    """
    text = "请选择上传图片的类型:"
    await main_msg.update_on_callback(
        callback,
        text,
        get_main_image_upload_type_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.in_([
    MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload:sfw",
    MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload:nsfw"
]))
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_upload_process(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """进入具体类型的上传状态"""
    is_nsfw = callback.data.endswith(":nsfw")
    await state.set_state(AdminMainImageState.waiting_for_image)
    await state.update_data(is_nsfw=is_nsfw)
    
    type_text = "NSFW" if is_nsfw else "SFW"
    text = (
        f"请发送 {type_text} 图片:\n"
        r"\- 支持 Photo\(推荐, 自动记录宽高\)" + "\n"
        r"\- 支持 Document\(图片文件\)" + "\n\n"
        "可附带说明作为 caption。"
    )
    
    await main_msg.update_on_callback(
        callback,
        text,
        get_main_image_cancel_keyboard()
    )
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_image)
async def handle_image_upload(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理图片上传
    
    功能说明:
    - 接收管理员发送的 Photo 或 Document(图片)
    - 提取文件ID与基础元数据并写入 main_images 表
    
    输入参数:
    - message: 管理员消息
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass

    file_id: str | None = None
    source_type = "photo"
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    caption = message.caption or ""

    if message.photo:
        p = message.photo[-1]
        file_id = p.file_id
        width = p.width
        height = p.height
        file_size = p.file_size
        source_type = "photo"
    elif message.document:
        doc = message.document
        if doc.mime_type and doc.mime_type.startswith("image/"):
            file_id = doc.file_id
            mime_type = doc.mime_type
            file_size = doc.file_size
            source_type = "document"
        else:
            await message.answer("❌ 仅支持图片文档，请重试。")
            return
    else:
        await message.answer("❌ 未检测到图片，请发送 Photo 或 图片 Document。")
        return

    # 获取当前上传类型
    data = await state.get_data()
    is_nsfw = data.get("is_nsfw", False)

    model = MainImageModel(
        file_id=file_id,
        source_type=source_type,
        mime_type=mime_type,
        width=width,
        height=height,
        file_size=file_size,
        caption=caption,
        is_nsfw=is_nsfw,  # 使用状态中的设置
    )
    session.add(model)
    await session.commit()

    safe_caption = escape_markdown_v2(caption)
    type_text = "NSFW" if is_nsfw else "SFW"
    text = (
        f"✅ {type_text} 图片上传成功\!" + "\n"
        f"ID: `{model.id}`" + "\n"
        f"Type: `{source_type}`" + "\n"
        f"Size: `{width}x{height}`" + "\n"
        f"Caption: {safe_caption}"
    )
    # 上传成功后清除状态，显示成功键盘(含继续上传)
    await state.clear()
    await main_msg.render(message.from_user.id, text, get_main_image_upload_success_keyboard(is_nsfw))
