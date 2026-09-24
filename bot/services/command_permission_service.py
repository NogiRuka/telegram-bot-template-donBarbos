"""通用命令授权服务。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import CommandPermissionModel, CommandPermissionScope
from bot.utils.datetime import now


def build_command_scope_key(
    scope_type: CommandPermissionScope,
    scope_id: int | str | None = None,
) -> str:
    """生成可用于唯一约束和查询的稳定作用域标识。"""
    if scope_type == CommandPermissionScope.GLOBAL:
        if scope_id is not None:
            msg = "全局命令授权不能指定 scope_id"
            raise ValueError(msg)
        return CommandPermissionScope.GLOBAL.value

    if scope_id is None or not str(scope_id).strip():
        msg = "群组命令授权必须指定 scope_id"
        raise ValueError(msg)
    return f"{CommandPermissionScope.GROUP.value}:{scope_id}"


async def has_command_permission(
    session: AsyncSession,
    user_id: int,
    command_name: str,
    scope_type: CommandPermissionScope,
    scope_id: int | str | None = None,
) -> bool:
    """检查用户是否具有指定作用域中的命令权限。"""
    scope_key = build_command_scope_key(scope_type, scope_id)
    stmt = select(CommandPermissionModel.id).where(
        CommandPermissionModel.user_id == user_id,
        CommandPermissionModel.command_name == command_name,
        CommandPermissionModel.scope_key == scope_key,
        CommandPermissionModel.is_deleted.is_(False),
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def list_command_permissions(
    session: AsyncSession,
    command_name: str,
    scope_type: CommandPermissionScope,
    scope_id: int | str | None = None,
) -> list[int]:
    """列出指定作用域和命令的全部有效授权用户。"""
    scope_key = build_command_scope_key(scope_type, scope_id)
    stmt = select(CommandPermissionModel.user_id).where(
        CommandPermissionModel.command_name == command_name,
        CommandPermissionModel.scope_key == scope_key,
        CommandPermissionModel.is_deleted.is_(False),
    )
    return list((await session.execute(stmt)).scalars().all())


async def set_command_permission(
    session: AsyncSession,
    user_id: int,
    command_name: str,
    scope_type: CommandPermissionScope,
    granted_by_user_id: int,
    enabled: bool,
    scope_id: int | str | None = None,
) -> bool:
    """授予或撤销命令权限，返回授权记录是否发生变化。"""
    scope_key = build_command_scope_key(scope_type, scope_id)
    stmt = select(CommandPermissionModel).where(
        CommandPermissionModel.user_id == user_id,
        CommandPermissionModel.command_name == command_name,
        CommandPermissionModel.scope_key == scope_key,
    )
    record = (await session.execute(stmt)).scalar_one_or_none()

    if enabled:
        if record is None:
            session.add(
                CommandPermissionModel(
                    user_id=user_id,
                    command_name=command_name,
                    scope_type=scope_type.value,
                    scope_key=scope_key,
                    granted_by_user_id=granted_by_user_id,
                    created_by=granted_by_user_id,
                )
            )
            return True
        if not record.is_deleted:
            return False
        record.is_deleted = False
        record.deleted_at = None
        record.deleted_by = None
        record.granted_by_user_id = granted_by_user_id
        record.updated_by = granted_by_user_id
        return True

    if record is None or record.is_deleted:
        return False
    record.is_deleted = True
    record.deleted_at = now()
    record.deleted_by = granted_by_user_id
    return True
