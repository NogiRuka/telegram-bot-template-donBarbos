from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.config import ConfigType
from bot.keyboards.inline.buttons import BACK_TO_HOME_BUTTON, BACK_TO_ADMIN_PANEL_BUTTON
from bot.keyboards.inline.constants import HITOKOTO_LABEL
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature, require_admin_priv

router = Router(name="admin_hitokoto")


def _get_hitokoto_types() -> tuple[dict[str, str], list[str]]:
    """获取一言分类映射"""
    type_names = {
        "a": "动画",
        "b": "漫画",
        "c": "游戏",
        "d": "文学",
        "e": "原创",
        "f": "来自网络",
        "g": "其他",
        "h": "影视",
        "i": "诗词",
        "j": "网易云",
        "k": "哲学",
        "l": "抖机灵",
    }
    all_types = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
    return type_names, all_types


def _build_hitokoto_ui(categories: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    """构建一言管理界面UI

    功能说明:
    - 生成统一的说明文本和键盘

    输入参数:
    - categories: 当前选中的分类列表

    返回值:
    - tuple[str, InlineKeyboardMarkup]: (文本, 键盘)
    """
    type_names, all_types = _get_hitokoto_types()
    
    # Build Keyboard
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for idx, ch in enumerate(all_types, start=1):
        enabled = ch in categories
        name = type_names.get(ch, ch)
        label = f"{name} {'🟢' if enabled else '🔴'}"
        current_row.append(InlineKeyboardButton(text=label, callback_data=f"admin:hitokoto:toggle:{ch}"))
        if idx % 4 == 0:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    rows.append([BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    # Build Caption
    current_names = [type_names.get(ch, ch) for ch in categories]
    caption = (
        f"{HITOKOTO_LABEL}\n\n"
        "选择需要纳入的分类参数（多选）：\n"
        "a 动画 | b 漫画 | c 游戏 | d 文学 | e 原创\n"
        "f 来自网络 | g 其他 | h 影视 | i 诗词 | j 网易云\n"
        "k 哲学 | l 抖机灵\n\n"
        f"当前分类：{', '.join(current_names) if current_names else '未选择'}\n"
        "提示：可多次点击切换，选择会即时保存。"
    )
    
    return caption, kb


@router.callback_query(F.data == "admin:hitokoto")
@require_admin_priv
@require_admin_feature("admin.hitokoto")
async def open_hitokoto_feature(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """打开一言管理功能

    功能说明:
    - 在管理员面板中展示一言分类选择面板, 使用中文分类名, 每行四个按钮, 底部提供返回与返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    categories = await get_config(session, "admin.hitokoto.categories") or []
    caption, kb = _build_hitokoto_ui(categories)
    await main_msg.update_on_callback(callback, caption, kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:hitokoto:toggle:"))
@require_admin_priv
@require_admin_feature("admin.hitokoto")
async def admin_hitokoto_toggle(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """切换一言分类

    功能说明:
    - 切换指定分类选中状态, 实时更新配置但不关闭面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    try:
        data = callback.data or ""
        ch = data.split(":")[-1]
        categories = await get_config(session, "admin.hitokoto.categories") or []
        if ch in categories:
            categories = [c for c in categories if c != ch]
        else:
            categories.append(ch)
            
        operator_id = callback.from_user.id if getattr(callback, "from_user", None) else None
        await set_config(
            session,
            "admin.hitokoto.categories",
            categories,
            ConfigType.LIST,
            operator_id=operator_id,
        )
        
        caption, kb = _build_hitokoto_ui(categories)
        await main_msg.update_on_callback(callback, caption, kb)
        await callback.answer("已更新分类")
        
    except (ValueError, TelegramBadRequest):
        await callback.answer("操作失败", show_alert=True)
