from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ADMIN_FEATURES_MAPPING, USER_FEATURES_MAPPING
from bot.services.config_service import list_admin_features, list_user_features, toggle_config
from bot.utils.permissions import require_owner

router = Router(name="owner_features")

COMMAND_META = {
    "name": "feature",
    "alias": "f",
    "usage": "/feature [user|admin] <code>",
    "desc": "查看或切换用户/管理员功能开关"
}


def _format_feature_lines(
    features: dict[str, bool],
    mapping: dict[str, tuple[str, str]],
) -> list[str]:
    lines: list[str] = []
    for short_code, (cfg_key, label) in mapping.items():
        enabled = features.get(cfg_key, False)
        status = "🟢" if enabled else "🔴"
        lines.append(f"{status} {label} ({short_code})")
    return lines


@router.message(Command("feature", "f"))
@require_owner
async def feature_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    args_raw = (command.args or "").strip()

    if not args_raw:
        user_features = await list_user_features(session)
        admin_features = await list_admin_features(session)

        text_parts: list[str] = []
        text_parts.append("📜 功能开关状态")
        text_parts.append("")
        text_parts.append("👤 用户功能:")
        text_parts.extend(_format_feature_lines(user_features, USER_FEATURES_MAPPING))
        text_parts.append("")
        text_parts.append("👮 管理功能:")
        text_parts.extend(_format_feature_lines(admin_features, ADMIN_FEATURES_MAPPING))

        await message.reply("\n".join(text_parts), parse_mode=None)
        return

    parts = args_raw.split()
    scope = parts[0]
    short_code = parts[1] if len(parts) > 1 else ""

    if scope not in {"user", "admin"} or not short_code:
        await message.reply("用法: /feature [user|admin] <code>", parse_mode=None)
        return

    mapping = USER_FEATURES_MAPPING if scope == "user" else ADMIN_FEATURES_MAPPING

    if short_code not in mapping:
        await message.reply(f"无效的 code: {short_code}", parse_mode=None)
        return

    cfg_key, label = mapping[short_code]
    operator_id = message.from_user.id if message.from_user else None
    new_val = await toggle_config(session, cfg_key, operator_id=operator_id)

    status = "🟢 启用" if new_val else "🔴 禁用"
    scope_label = "用户" if scope == "user" else "管理员"
    await message.reply(f"{status} {scope_label}功能: {label} ({short_code})", parse_mode=None)

