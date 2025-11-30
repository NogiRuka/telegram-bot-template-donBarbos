from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="user_profile")


@router.callback_query(F.data == "user:profile")
async def user_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    """个人信息

    功能说明:
    - 展示个人信息入口, 当前为占位实现

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    if session is None:
        pass
    try:
        await callback.answer("功能建设中, 请稍后再试", show_alert=True)
    except TelegramAPIError:
        await callback.answer("❌ 系统异常, 请稍后再试", show_alert=True)

