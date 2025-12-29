from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.database.models import MainImageModel
from bot.keyboards.inline.admin import get_main_image_back_keyboard
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature
from .router import router

@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def list_images(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示图片列表
    
    功能说明:
    - 列出最近 10 条图片并提供查看与操作入口
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    result = await session.execute(
        select(MainImageModel).where(MainImageModel.is_deleted.is_(False)).order_by(MainImageModel.id.desc()).limit(10)
    )
    items = list(result.scalars().all())
    if not items:
        # 即使没有图片，也应该更新主消息而不是弹窗，保持一致性
        await main_msg.update_on_callback(callback, "🈚️ 暂无图片，请先上传。", get_main_image_back_keyboard())
        await callback.answer()
        return
    lines = ["*🗂 图片列表*"]
    for it in items:
        # 手动转义特殊字符
        lines.append(
            fr"\- ID `{it.id}` \| {'NSFW' if it.is_nsfw else 'SFW'} \| {'启用' if it.is_enabled else '禁用'}"
        )
    lines.append("\n使用 /start 可在用户端验证展示效果。")
    await main_msg.update_on_callback(callback, "\n".join(lines), get_main_image_back_keyboard())
    await callback.answer()
