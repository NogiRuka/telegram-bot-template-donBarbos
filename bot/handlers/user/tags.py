from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from bot.utils.permissions import require_user_feature
from bot.utils.images import get_common_image
from bot.keyboards.inline.user import get_user_tags_keyboard
from bot.services.main_message import MainMessageService

router = Router(name="user_tags")

@router.callback_query(F.data == "user:tags")
@require_user_feature("user.tags")
async def user_tags(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """处理标签屏蔽

    功能说明:
    - 显示当前标签屏蔽状态
    - 提供标签管理功能入口

    输入参数:
    - callback: 回调查询对象
    - session: 数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    text = "🎯 标签屏蔽功能开发中..."
    text += f"\n\n当前屏蔽标签: (暂无)"
    
    # 获取账号中心键盘布局
    kb = get_user_tags_keyboard()
    image = get_common_image()
    
    await main_msg.update_on_callback(callback, text, kb, image)
    await callback.answer()