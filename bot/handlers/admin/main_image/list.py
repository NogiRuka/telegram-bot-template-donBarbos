from math import ceil

from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.database.models import MainImageModel
from bot.keyboards.inline.admin import (
    get_main_image_list_type_keyboard,
    get_main_image_list_pagination_keyboard,
    get_main_image_item_keyboard
)
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature
from bot.utils.message import send_toast
from bot.utils.text import escape_markdown_v2
from .router import router


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def list_images_entry(callback: CallbackQuery, main_msg: MainMessageService) -> None:
    """进入图片列表 - 选择类型"""
    text = "请选择要查看的图片类型:"
    await main_msg.update_on_callback(callback, text, get_main_image_list_type_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith(MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list:view:"))
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def list_images_view(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示图片列表（分页）"""
    # Parse: admin:main_image:list:view:sfw:1:5
    try:
        parts = callback.data.split(":")
        type_key = parts[4]  # sfw / nsfw
        page = int(parts[5])
        limit = int(parts[6])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    is_nsfw = (type_key == "nsfw")
    
    # Count total
    count_stmt = select(func.count()).where(
        MainImageModel.is_deleted.is_(False),
        MainImageModel.is_nsfw == is_nsfw
    )
    total_count = (await session.execute(count_stmt)).scalar_one()
    total_pages = ceil(total_count / limit) if total_count > 0 else 1
    
    # Adjust page if out of bounds
    if page > total_pages:
        page = total_pages
    if page < 1:
        page = 1

    # Query items
    stmt = (
        select(MainImageModel)
        .where(
            MainImageModel.is_deleted.is_(False),
            MainImageModel.is_nsfw == is_nsfw
        )
        .order_by(MainImageModel.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = (await session.execute(stmt)).scalars().all()

    # Update Control Message
    type_name = "NSFW" if is_nsfw else "SFW"
    text = (
        f"*🗂 图片列表 ({type_name})*\n"
        f"共 {total_count} 张，当前第 {page}/{total_pages} 页"
    )
    await main_msg.update_on_callback(
        callback, 
        text, 
        get_main_image_list_pagination_keyboard(type_key, page, total_pages, limit)
    )
    
    # Send Images
    if not items:
        await send_toast(callback, "暂无数据")
        return

    for item in items:
        # Construct caption
        width = item.width if item.width is not None else "?"
        height = item.height if item.height is not None else "?"
        
        caption = (
            f"🆔 ID: `{item.id}`\n"
            f"📝 说明: {escape_markdown_v2(item.caption or '无')}\n"
            f"📐 尺寸: {width}x{height}\n"
            f"⚙️ 状态: {'🟢 启用' if item.is_enabled else '🔴 禁用'}"
        )
        
        try:
            # 统一使用 MarkdownV2
            kwargs = {
                "caption": caption,
                "reply_markup": get_main_image_item_keyboard(item.id, item.is_enabled),
                "parse_mode": "MarkdownV2"
            }
            
            if item.source_type == "document":
                await callback.message.answer_document(document=item.file_id, **kwargs)
            else:
                await callback.message.answer_photo(photo=item.file_id, **kwargs)
        except Exception as e:
             await callback.message.answer(f"❌ 图片 ID `{item.id}` 加载失败: {e}")

    await callback.answer()


@router.callback_query(F.data.startswith(MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":item:"))
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def item_action(callback: CallbackQuery, session: AsyncSession) -> None:
    # Parse: admin:main_image:item:toggle:123
    try:
        parts = callback.data.split(":")
        action = parts[3]
        
        if action == "close":
            await callback.message.delete()
            return

        item_id = int(parts[4])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    item = await session.get(MainImageModel, item_id)
    if not item:
        await callback.answer("❌ 图片不存在", show_alert=True)
        await callback.message.delete()
        return

    if action == "toggle":
        item.is_enabled = not item.is_enabled
        await session.commit()
        
        # Update caption to reflect status
        caption = (
            f"🆔 ID: `{item.id}`\n"
            f"📝 说明: {escape_markdown_v2(item.caption or '无')}\n"
            f"📐 尺寸: {item.width}x{item.height}\n"
            f"⚙️ 状态: {'🟢 启用' if item.is_enabled else '🔴 禁用'}"
        )
        try:
             await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_main_image_item_keyboard(item.id, item.is_enabled),
                parse_mode="MarkdownV2"
            )
        except Exception:
            pass 
            
        await callback.answer(f"已{'启用' if item.is_enabled else '禁用'}")

    elif action == "delete":
        # Soft delete
        item.is_deleted = True
        await session.commit()
        await callback.message.delete()
        await callback.answer("已删除")
