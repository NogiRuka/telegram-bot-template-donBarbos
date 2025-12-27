from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ADMIN_FEATURES_MAPPING
from bot.keyboards.inline.constants import ADMIN_FEATURES_PANEL_LABEL
from bot.keyboards.inline.owner import get_admin_features_panel_keyboard
from bot.services.config_service import list_admin_features, toggle_config
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_owner

router = Router(name="owner_admin_features")


@router.callback_query(F.data == "owner:admin_features")
@require_owner
async def show_admin_features_panel(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """展示管理员功能面板

    功能说明:
    - 显示管理员功能开关列表, 支持返回上一级与返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    features = await list_admin_features(session)
    kb = get_admin_features_panel_keyboard(features)

    await main_msg.update_on_callback(callback, ADMIN_FEATURES_PANEL_LABEL, kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("owner:admin_features:toggle:"))
@require_owner
async def toggle_admin_features(
    callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService
) -> None:
    """统一切换管理员功能开关

    功能说明:
    - 处理 `owner:admin_features:toggle:*` 的所有管理员功能开关, 统一翻转配置并刷新功能面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    parts = (callback.data or "").split(":")
    min_parts = 4
    key = parts[-1] if len(parts) >= min_parts else ""

    if not key or key not in ADMIN_FEATURES_MAPPING:
        await callback.answer("🔴 无效的权限项", show_alert=True)
        return

    try:
        config_key, label = ADMIN_FEATURES_MAPPING[key]
        operator_id = callback.from_user.id if getattr(callback, "from_user", None) else None
        new_val = await toggle_config(session, config_key, operator_id=operator_id)
        features = await list_admin_features(session)
    except SQLAlchemyError:
        await callback.answer("🔴 操作失败, 请稍后重试", show_alert=True)
        return

    await main_msg.update_on_callback(
        callback, ADMIN_FEATURES_PANEL_LABEL, get_admin_features_panel_keyboard(features)
    )
    await callback.answer(f"{'🟢' if new_val else '🔴'} {label}: {'启用' if new_val else '禁用'}")
