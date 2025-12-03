from aiogram import F, Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.config_service import get_config
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature, require_admin_priv

router = Router(name="admin_hitokoto")


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
    type_names: dict[str, str] = {
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

    rows.append(
        [
            InlineKeyboardButton(text="⬅️ 返回", callback_data="admin:panel"),
            InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"),
        ]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    current_names = [type_names.get(ch, ch) for ch in categories]
    desc = (
        "📝 一言管理\n\n"
        "选择需要纳入的分类参数(多选):\n"
        "a 动画 | b 漫画 | c 游戏 | d 文学 | e 原创\n"
        "f 来自网络 | g 其他 | h 影视 | i 诗词 | j 网易云\n"
        "k 哲学 | l 抖机灵\n\n"
        f"当前分类: {', '.join(current_names) if current_names else '未选择'}\n"
        "提示: 可多次点击切换, 选择会即时保存。"
    )
    msg = callback.message
    if isinstance(msg, types.Message):
        await main_msg.update_by_message(msg, desc, kb)
    await callback.answer()
