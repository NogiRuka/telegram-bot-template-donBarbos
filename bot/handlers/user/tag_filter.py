from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import UserModel
from bot.services.config_service import get_config
from bot.services.main_message import MainMessageService
from bot.keyboards.inline.common_buttons import BACK_BUTTON
from bot.features import register_user_feature

# 1. 定义功能 (Single Source of Truth)
tag_filter_feature = register_user_feature(
    name="user.tag_filter",
    label="标签屏蔽",
    description="管理用户屏蔽的标签关键词，过滤相关内容",
    enabled=True,
    show_in_panel=True,
    button_order=60,
)

# 2. 创建路由器 (自动生成)
router = tag_filter_feature.create_router()

# 3. 使用功能对象 (无需重复字符串)
@router.callback_query(tag_filter_feature.filter)
@tag_filter_feature.require
async def handle_tag_filter(
    callback_query: CallbackQuery, 
    session: AsyncSession,
    user: UserModel,
    main_message_service: MainMessageService,
):
    """处理标签屏蔽"""
    
    # 检查功能是否启用 (使用 config_key)
    config_value = await get_config(session, tag_filter_feature.config_key)
    is_enabled = bool(config_value) if config_value is not None else tag_filter_feature.enabled
    
    if not is_enabled:
        await callback_query.answer("标签屏蔽功能已关闭", show_alert=True)
        return

    text = "🎯 标签屏蔽功能开发中..."
    text += f"\n\n当前屏蔽标签: (暂无)"
    
    await main_message_service.update_message(
        text=text,
        reply_markup=BACK_BUTTON,
    )
