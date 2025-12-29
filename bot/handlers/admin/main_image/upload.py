from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.database.models import MainImageModel
from bot.keyboards.inline.admin import get_main_image_cancel_keyboard, get_main_image_back_keyboard
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.admin import AdminMainImageState
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2
from .router import router

@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_upload(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始上传流程
    
    功能说明:
    - 进入等待图片或文件消息的状态, 指引管理员发送照片或图片文档
    
    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    await state.set_state(AdminMainImageState.waiting_for_image)
    text = (
        "请发送图片:\n"
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

    model = MainImageModel(
        file_id=file_id,
        source_type=source_type,
        mime_type=mime_type,
        width=width,
        height=height,
        file_size=file_size,
        is_nsfw=False,
        is_enabled=True,
        caption=caption or None,
    )
    session.add(model)
    await session.commit()

    text = (
        f"✅ 上传成功\n\n"
        f"ID: {model.id}\n"
        f"类型: {escape_markdown_v2(source_type)}\n"
        f"尺寸: {width or '-'} x {height or '-'}\n"
        f"大小: {escape_markdown_v2(str(file_size or 0))}B\n"
        f"NSFW: {'是' if model.is_nsfw else '否'}\n"
        f"启用: {'是' if model.is_enabled else '否'}\n"
    )
    # 上传成功后清除状态，显示返回键盘
    await state.clear()
    await main_msg.render(message.from_user.id, text, get_main_image_back_keyboard())
