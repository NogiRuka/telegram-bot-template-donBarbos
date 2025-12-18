from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from bot.utils.permissions import require_user_feature

from bot.services.main_message import MainMessageService

router = Router(name="user_tags")

@router.callback_query(F.data == "user:tags")
@require_user_feature("user.tags")
async def user_tags(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """处理标签屏蔽"""

    text = "🎯 标签屏蔽功能开发中..."
    text += f"\n\n当前屏蔽标签: (暂无)"
    
    kb = get_account_center_keyboard(user_has_emby)
    image = get_common_image()
    await main_msg.update_on_callback(callback, text, kb, image)
    await callback.answer()