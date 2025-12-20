from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.constants import (
    FEATURES_PANEL_LABEL,
    ROBOT_SWITCH_LABEL,
)
from bot.keyboards.inline.owner import get_features_panel_keyboard
from bot.services.config_service import (
    KEY_BOT_FEATURES_ENABLED,
    OWNER_FEATURES_MAPPING,
    list_features,
    toggle_config,
)
from bot.services.main_message import MainMessageService
from bot.utils.images import get_common_image
from bot.utils.permissions import require_owner

router = Router(name="owner_features")


@router.callback_query(F.data == "owner:features")
@require_owner
async def show_features_panel(
    callback: CallbackQuery, 
    session: AsyncSession, 
    main_msg: MainMessageService
) -> None:
    """显示功能开关面板

    功能说明:
    - 跳转到功能开关子面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    features = await list_features(session)
    kb = get_features_panel_keyboard(features)
    image = get_common_image()
    
    await main_msg.update_on_callback(callback, FEATURES_PANEL_LABEL, kb, image_path=image)
    await callback.answer()


@router.callback_query(F.data == "owner:toggle:bot")
@require_owner
async def toggle_bot_enabled(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换机器人总开关

    功能说明:
    - 翻转 `bot.features.enabled` 状态并返回提示

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, KEY_BOT_FEATURES_ENABLED)
    await callback.answer(f"{'🟢' if new_val else '🔴'} {ROBOT_SWITCH_LABEL}: {'开启' if new_val else '关闭'}")


@router.callback_query(lambda c: c.data and c.data.startswith("owner:features:toggle:"))
@require_owner
async def toggle_owner_features(
    callback: CallbackQuery, 
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """统一切换所有者功能开关

    功能说明:
    - 处理 `owner:features:toggle:*` 的所有功能开关, 统一翻转配置并刷新功能面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    try:
        parts = (callback.data or "").split(":")
        key = parts[-1] if len(parts) >= 4 else ""
        
        if key not in OWNER_FEATURES_MAPPING:
            await callback.answer("🔴 无效的开关项", show_alert=True)
            return
            
        config_key, label = OWNER_FEATURES_MAPPING[key]
        operator_id = callback.from_user.id if getattr(callback, "from_user", None) else None
        new_val = await toggle_config(session, config_key, operator_id=operator_id)
        features = await list_features(session)
        
        await main_msg.update_on_callback(
            callback, 
            FEATURES_PANEL_LABEL, 
            get_features_panel_keyboard(features),
            image_path=get_common_image()
        )
        await callback.answer(f"{'🟢' if new_val else '🔴'} {label}: {'启用' if new_val else '禁用'}")
    except Exception:
        await callback.answer("🔴 操作失败，请稍后重试", show_alert=True)

