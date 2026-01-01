from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.users import is_admin

router = Router()

@router.message(Command("command", "c"))
async def cmd_list_commands(message: types.Message, session: AsyncSession) -> None:
    """
    显示可用命令列表
    """
    # 基础命令 (对所有用户可见)
    # 注意: MarkdownV2 需要转义特殊字符 (如 -, ., (, ), !) 但保留 * 用于加粗
    text = r"""
📜 *可用命令列表*

👤 *用户命令*
• /start \- 开始使用/查看欢迎信息
• /help \- 获取帮助
• /info \- 查看个人信息
• /gf \<唯一名\> \- 获取文件 \(支持多个\)
• /c, /command \- 显示此命令列表

📝 *其他*
• 直接发送文件 \- 上传文件
"""

    # 管理员命令 (仅管理员可见)
    if message.from_user and await is_admin(session, message.from_user.id):
        admin_text = r"""
👮 *管理员命令*
• /gen\_gf /ggf \<ID\>\.\.\. \- 生成获取命令
• /group\_config, /gc \- 查看/修改群组配置 \(群组\)
• /group\_config \<ID\> \- 查看群组配置 \(私聊\)

👥 *群组功能*
• 回复文件 /save \- 保存文件 \(群组\)
"""
        text += "\n" + admin_text

    await message.reply(text, parse_mode="MarkdownV2")
