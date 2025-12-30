from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("command", "c"))
async def cmd_list_commands(message: types.Message) -> None:
    """
    显示可用命令列表
    """
    text = """
📜 *可用命令列表*

👤 *用户命令*
• /start - 开始使用/查看欢迎信息
• /help - 获取帮助
• /info - 查看个人信息
• /gf <唯一名> - 获取文件
• /c, /command - 显示此命令列表

👥 *群组命令* (仅管理员)
• /group_config, /gc - 查看/修改群组配置
• /group_config <ID/@username> - 私聊查看群组配置

📝 *其他*
• 直接发送文件 - 上传文件
• 回复文件 /save - 保存文件 (群组)
"""
    await message.reply(text, parse_mode="Markdown")
