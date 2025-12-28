from urllib.parse import urlparse

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import KEY_USER_LINES_INFO, KEY_USER_LINES_NOTICE
from bot.keyboards.inline.buttons import BACK_TO_HOME_BUTTON, BACK_TO_ACCOUNT_BUTTON
from bot.services.config_service import get_config
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_user_feature
from bot.utils.text import escape_markdown_v2

router = Router(name="user_lines")


@router.callback_query(F.data == "user:lines")
@require_user_feature("user.lines")
async def user_lines(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """线路信息

    功能说明:
    - 展示服务器线路信息(地址与端口)
    - 仅从数据库配置读取

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    # 尝试从数据库获取自定义线路信息
    # 预期存储格式为 JSON 字典或 URL 字符串
    db_lines_info = await get_config(session, KEY_USER_LINES_INFO)
    notice = await get_config(session, KEY_USER_LINES_NOTICE)
    
    host = "未设置"
    port = "未设置"

    if db_lines_info:
        if isinstance(db_lines_info, dict):
            # 优先处理字典格式
            host = db_lines_info.get("host", "未设置")
            port = str(db_lines_info.get("port", "未设置"))
        elif isinstance(db_lines_info, str):
            # 兼容旧的字符串格式 (自动回退逻辑会存入字典，这里是防守)
            target_url = db_lines_info
            # 简单的 URL 解析补全
            if not target_url.startswith(("http://", "https://")):
                target_url = f"http://{target_url}"
                
            try:
                parsed = urlparse(target_url)
                host = parsed.hostname or target_url
                port = str(parsed.port) if parsed.port else ("443" if parsed.scheme == "https" else "80")
            except Exception:
                host = target_url
                port = "未知"

    # 构建显示内容
    lines_text = [
        "📡 *线路信息*",
        "",
        f"🌐 服务器地址: `{escape_markdown_v2(str(host))}`",
        f"🔌 端口: `{escape_markdown_v2(str(port))}`",
    ]

    if notice:
        lines_text.extend([
            "",
            notice,
        ])
    
    caption = "\n".join(lines_text)
    
    # 构建键盘
    kb = InlineKeyboardMarkup(inline_keyboard=[[BACK_TO_ACCOUNT_BUTTON,BACK_TO_HOME_BUTTON]])
    
    await main_msg.update_on_callback(callback, caption, kb)
    await callback.answer()
