"""
功能生成器工具

功能说明:
- 快速生成新功能的完整代码
- 自动生成处理器、按钮、配置
- 支持一键注册功能

使用示例:
    python -m bot.tools.generate_feature --name user.demo --label "演示功能"
"""

import argparse
from pathlib import Path


def generate_feature_handler(name: str, label: str, description: str = "") -> str:
    """生成功能处理器代码"""
    feature_key = name.replace(".", "_")
    handler_name = name.replace(".", "_").replace("user_", "handle_")

    return f'''"""
{label}功能处理器

功能说明:
{description or f"处理 {label} 相关逻辑"}
"""

from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.config_service import get_config_bool
from bot.services.main_message import MainMessageService
from bot.config import KEY_{feature_key.upper()}
from bot.utils.permissions import require_user_feature
from bot.keyboards.inline.common_buttons import get_back_button


@require_user_feature("{name}")
async def {handler_name}(
    callback_query: CallbackQuery,
    session: AsyncSession,
    main_message_service: MainMessageService,
) -> None:
    """
    处理{label}

    功能说明:
    - 处理用户的{label}请求
    - 返回相应的信息或界面

    输入参数:
    - callback_query: 回调查询对象
    - session: 数据库会话
    - main_message_service: 主消息服务

    返回值:
    - 无
    """

    # 检查功能是否启用
    if not await get_config_bool(session, KEY_{feature_key.upper()}):
        await callback_query.answer("{label}功能已关闭", show_alert=True)
        return

    # TODO: 实现具体的{label}逻辑
    text = "🎯 {label}功能开发中..."

    # 更新消息
    await main_message_service.update_message(
        text=text,
        reply_markup=get_back_button(),
    )

    await callback_query.answer()


# 导出处理器
__all__ = ["{handler_name}"]
'''


def generate_feature_registration(name: str, label: str, description: str = "") -> str:
    """生成功能注册代码"""
    handler_name = name.replace(".", "_").replace("user_", "handle_")

    return f'''"""
{name}功能注册

功能说明:
注册{name}功能到系统中
"""

from bot.features import register_user_feature
from bot.handlers.user.{name.replace(".", "_")} import {handler_name}


def register_{name.replace(".", "_")}_feature():
    """注册{name}功能"""
    register_user_feature(
        name="{name}",
        label="{label}",
        description="{description or f"用户{label}功能"}",
        handler={handler_name},
        enabled=True,
        show_in_panel=True,
        button_order=50,  # 调整按钮排序
    )


# 注册功能
register_{name.replace(".", "_")}_feature()
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="生成功能代码")
    parser.add_argument("--name", required=True, help="功能名称 (如: user.demo)")
    parser.add_argument("--label", required=True, help="功能标签")
    parser.add_argument("--description", default="", help="功能描述")
    parser.add_argument("--output-dir", default="bot/handlers/user", help="输出目录")

    args = parser.parse_args()

    # 生成处理器文件
    handler_code = generate_feature_handler(args.name, args.label, args.description)
    handler_file = Path(args.output_dir) / f"{args.name.replace('.', '_')}.py"

    # 确保目录存在
    handler_file.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(handler_file, "w", encoding="utf-8") as f:
        f.write(handler_code)


    # 生成注册文件
    registration_code = generate_feature_registration(args.name, args.label, args.description)
    registration_file = Path("bot/features/registrations") / f"{args.name.replace('.', '_')}.py"

    # 确保目录存在
    registration_file.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(registration_file, "w", encoding="utf-8") as f:
        f.write(registration_code)


    # 输出使用说明



if __name__ == "__main__":
    main()
