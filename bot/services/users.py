from __future__ import annotations
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import func, select, update

from bot.cache import build_key, cached, clear_cache
from bot.core.config import settings
from bot.database.models import UserExtendModel, UserHistoryModel, UserModel, UserRole
from bot.utils.datetime import now

if TYPE_CHECKING:
    from aiogram.types import User
    from sqlalchemy.ext.asyncio import AsyncSession


async def add_user(session: AsyncSession, user: User) -> None:
    """新增用户

    功能说明:
    - 将 aiogram `User` 写入 `users` 表；保存核心字段
    - 额外保存 `is_bot`、`is_premium`、`added_to_attachment_menu`
    - 提交后更新缓存

    输入参数:
    - session: 异步数据库会话
    - user: aiogram User 实例

    返回值:
    - None
    """
    try:
        user_id: int = user.id

        def _normalize_bool(val: bool | None) -> bool | None:
            """布尔值归一化

            功能说明:
            - 将 None 保持为 None；非 None 转为 bool

            输入参数:
            - val: 布尔或 None

            返回值:
            - bool | None
            """
            return bool(val) if val is not None else None

        new_user = UserModel(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=_normalize_bool(getattr(user, "is_premium", None)),
            is_bot=bool(user.is_bot),
            added_to_attachment_menu=_normalize_bool(getattr(user, "added_to_attachment_menu", None)),
        )
        session.add(new_user)
        # 同步写入 user_extend（首次交互）

        ext_res = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user.id))
        ext = ext_res.scalar_one_or_none()
        if ext is None:
            session.add(
                UserExtendModel(
                    user_id=user.id,
                    last_interaction_at=now(),
                )
            )
        await session.commit()
        await clear_cache(user_exists, user_id)
    except Exception:
        # 降级：若失败则忽略新增
        pass


@cached(key_builder=lambda session, user_id: build_key(user_id))
async def user_exists(session: AsyncSession, user_id: int) -> bool:
    """Checks if the user is in the database."""
    query = select(UserModel.id).filter_by(id=user_id).limit(1)

    result = await session.execute(query)

    user = result.scalar_one_or_none()
    return bool(user)


@cached(key_builder=lambda session, user_id: build_key(user_id))
async def get_first_name(session: AsyncSession, user_id: int) -> str:
    query = select(UserModel.first_name).filter_by(id=user_id)

    result = await session.execute(query)

    first_name = result.scalar_one_or_none()
    return first_name or ""

    await session.commit()
    return None


@cached(key_builder=lambda session, user_id: build_key(user_id))
async def is_admin(session: AsyncSession, user_id: int) -> bool:
    """判断是否管理员

    功能说明:
    - 基于 `user_extend.role` 判断是否具备管理员权限（含 owner）

    输入参数:
    - session: 异步数据库会话
    - user_id: 用户 ID

    返回值:
    - bool: True 表示管理员或所有者
    """
    query = select(UserExtendModel.role).where(UserExtendModel.user_id == user_id)
    result = await session.execute(query)
    role = result.scalar_one_or_none()
    return role in {UserRole.admin, UserRole.owner}


async def save_user_snapshot(session: AsyncSession, user: User, remark: str | None = None) -> None:
    """保存用户信息快照

    功能说明:
    - 将 aiogram 用户信息保存到 `user_history`，用于历史追踪

    输入参数:
    - session: 异步数据库会话
    - user: aiogram User 实例
    - remark: 备注信息

    返回值:
    - None
    """
    try:

        def _normalize_bool(val: bool | None) -> bool | None:
            """布尔值归一化

            功能说明:
            - 将 None 保持为 None；非 None 转为 bool

            输入参数:
            - val: 布尔或 None

            返回值:
            - bool | None
            """
            return bool(val) if val is not None else None

        snapshot = UserHistoryModel(
            user_id=user.id,
            is_bot=bool(user.is_bot),
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=_normalize_bool(getattr(user, "is_premium", None)),
            added_to_attachment_menu=_normalize_bool(getattr(user, "added_to_attachment_menu", None)),
            remark=remark,
        )
        session.add(snapshot)
        await session.commit()
    except Exception:
        # 快照失败不影响主流程
        pass


async def save_user_snapshot_from_model(session: AsyncSession, model: UserModel, remark: str | None = None) -> None:
    """保存用户信息快照（基于当前数据库值）

    功能说明:
    - 将 `users` 表当前记录写入 `user_history`，用于在发生变更前保存旧值

    输入参数:
    - session: 异步数据库会话
    - model: 当前数据库中的用户模型实例
    - remark: 备注信息

    返回值:
    - None
    """
    try:
        snapshot = UserHistoryModel(
            user_id=model.id,
            is_bot=bool(model.is_bot),
            first_name=model.first_name,
            last_name=model.last_name,
            username=model.username,
            language_code=model.language_code,
            is_premium=model.is_premium,
            added_to_attachment_menu=model.added_to_attachment_menu,
            remark=remark,
        )
        session.add(snapshot)
        await session.commit()
    except Exception:
        pass


async def upsert_user_on_interaction(session: AsyncSession, user: User) -> None:
    """交互时更新用户信息

    功能说明:
    - 用户与机器人交互（消息/回调）时，更新 `users` 表的最新字段
    - 若用户不存在则创建；存在则覆盖可变字段
    - 更新 `user_extend.last_interaction_at`，必要时自动创建扩展记录
    - 保存一条 `user_history` 快照以便追踪变更

    输入参数:
    - session: 异步数据库会话
    - user: aiogram User 实例

    返回值:
    - None
    """
    try:

        def _normalize_bool(val: bool | None) -> bool | None:
            """布尔值归一化

            功能说明:
            - 将 None 保持为 None；非 None 转为 bool

            输入参数:
            - val: 布尔或 None

            返回值:
            - bool | None
            """
            return bool(val) if val is not None else None

        exists = await user_exists(session, user.id)
        if not exists:
            # 首次：写 users 与 user_extend；不写 user_history
            await add_user(session, user)
        else:
            res = await session.execute(select(UserModel).where(UserModel.id == user.id))
            current = res.scalar_one_or_none()
            if current:
                new_values = {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "language_code": user.language_code,
                    "is_premium": _normalize_bool(getattr(user, "is_premium", None)),
                    "is_bot": bool(user.is_bot),
                    "added_to_attachment_menu": _normalize_bool(getattr(user, "added_to_attachment_menu", None)),
                }
                changed = {k: v for k, v in new_values.items() if getattr(current, k) != v}
                if changed:
                    # 生成中文变更备注
                    changed_fields = []
                    for k, v in changed.items():
                        old_val = getattr(current, k)
                        changed_fields.append(f"{k} 从 {old_val} 更新为 {v}")
                    remark = "; ".join(changed_fields)

                    await save_user_snapshot_from_model(session, current, remark=remark)
                    await session.execute(update(UserModel).where(UserModel.id == user.id).values(**changed))
                    await session.commit()

        # 基于配置同步角色（owner/admin/user）
        await ensure_role_by_settings(session, user.id)

        # 更新扩展表最后交互时间（无则创建）
        ext_res = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user.id))
        ext = ext_res.scalar_one_or_none()
        if ext is None:
            session.add(
                UserExtendModel(
                    user_id=user.id,
                    last_interaction_at=now(),
                )
            )
            await session.commit()
        else:
            await session.execute(
                update(UserExtendModel)
                .where(UserExtendModel.user_id == user.id)
                .values(last_interaction_at=now(), updated_at=now())
            )
            await session.commit()
    except Exception:
        pass


async def ensure_role_by_settings(session: AsyncSession, user_id: int) -> None:
    """根据配置同步用户角色

    功能说明:
    - 对 `user_extend.role` 进行校正：与配置中的 `OWNER_ID`/`ADMIN_IDS` 对齐
    - 优先级：owner > admin > user

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID

    返回值:
    - None
    """
    try:
        desired = UserRole.user
        try:
            if user_id == settings.get_owner_id():
                desired = UserRole.owner
        except Exception:
            pass
        if desired is UserRole.user:
            admin_ids = set(settings.get_admin_ids())
            if user_id in admin_ids:
                desired = UserRole.admin

        res = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user_id))
        ext = res.scalar_one_or_none()
        if ext is None:
            model = UserExtendModel(user_id=user_id, role=desired)
            session.add(model)
            await session.commit()
            return
        if ext.role != desired:
            ext.role = desired
            await session.commit()
    except Exception:
        pass


async def set_is_admin(session: AsyncSession, user_id: int, is_admin: bool) -> None:
    """设置管理员角色

    功能说明:
    - 将 `user_extend.role` 设置为 `admin` 或 `user`

    输入参数:
    - session: 异步数据库会话
    - user_id: 用户 ID
    - is_admin: 是否管理员

    返回值:
    - None
    """
    target_role = UserRole.admin if is_admin else UserRole.user
    # upsert
    existing = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user_id))
    model = existing.scalar_one_or_none()
    if model:
        # 若当前为 owner，则不降级
        if model.role == UserRole.owner:
            return
        model.role = target_role
    else:
        model = UserExtendModel(user_id=user_id, role=target_role)
        session.add(model)
    await session.commit()


async def add_admin(session: AsyncSession, user_id: int) -> bool:
    """添加管理员

    功能说明:
    - 将指定用户的管理员标志设置为 True

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID

    返回值:
    - bool: True 表示操作成功
    """
    try:
        await set_is_admin(session, user_id, True)
        return True
    except Exception:
        return False


async def remove_admin(session: AsyncSession, user_id: int) -> bool:
    """移除管理员

    功能说明:
    - 将指定用户的管理员标志设置为 False

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID

    返回值:
    - bool: True 表示操作成功
    """
    try:
        await set_is_admin(session, user_id, False)
        return True
    except Exception:
        return False


@cached(key_builder=lambda session: build_key())
async def get_all_users(session: AsyncSession) -> list[UserModel]:
    query = select(UserModel)

    result = await session.execute(query)

    users = result.scalars()
    return list(users)


@cached(key_builder=lambda session: build_key())
async def get_user_count(session: AsyncSession) -> int:
    query = select(func.count()).select_from(UserModel)

    result = await session.execute(query)

    count = result.scalar_one_or_none() or 0
    return int(count)


@cached(key_builder=lambda session: build_key())
async def list_admins(session: AsyncSession) -> list[UserModel]:
    """列出管理员用户

    功能说明:
    - 基于 `user_extend.role in ('admin','owner')` 查询管理员/所有者对应的用户列表

    输入参数:
    - session: 异步数据库会话

    返回值:
    - list[UserModel]: 管理员列表
    """
    role_query = select(UserExtendModel.user_id).where(UserExtendModel.role.in_([UserRole.admin, UserRole.owner]))
    query = select(UserModel).where(UserModel.id.in_(role_query))
    result = await session.execute(query)
    users = result.scalars()
    return list(users)


async def create_and_bind_emby_user(
    session: AsyncSession, user_id: int, name: str, password: str
) -> tuple[bool, dict[str, str] | None, str | None]:
    """创建 Emby 用户并绑定到用户扩展表

    功能说明:
    - 检查是否已绑定 Emby 账号, 若未绑定则创建 Emby 用户并持久化本地快照
    - 将新创建的 `emby_user_id` 写入 `user_extend.emby_user_id`
    - 使用 emby_service.create_user 进行完整创建流程（含模板配置复制）

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID
    - name: Emby 用户名
    - password: Emby 密码

    返回值:
    - tuple[bool, dict[str, str] | None, str | None]:
      - 第1项: 是否成功
      - 第2项: 成功时返回字典 `{"name": 用户名, "password": 明文密码}`; 失败为 None
      - 第3项: 失败时的错误信息字符串; 成功为 None

    依赖安装:
    - pip install "aiohttp[speedups]"  # Emby API 请求
    - pip install bcrypt                # 密码哈希

    异步/同步:
    - 本函数为异步函数; Emby API 与数据库操作均需 `await`

    错误处理:
    - 捕获网络与数据库异常, 返回错误信息而非抛出, 避免上层崩溃
    """
    try:
        from sqlalchemy import select as _select
        from sqlalchemy.exc import SQLAlchemyError

        from bot.database.models import EmbyUserHistoryModel, EmbyUserModel
        from bot.handlers.emby import hash_password
        from bot.services import emby_service

        # 已绑定检查
        res_ext = await session.execute(_select(UserExtendModel).where(UserExtendModel.user_id == user_id))
        ext = res_ext.scalar_one_or_none()
        if ext and getattr(ext, "emby_user_id", None):
            logger.info("ℹ️ 用户已绑定 Emby 账号: user_id={} emby_user_id={}", user_id, getattr(ext, "emby_user_id", None))
            return False, None, "已绑定 Emby 账号"

        # 调用 emby_service.create_user 完整流程
        ok, user_dto, err = await emby_service.create_user(name=name, password=password)
        if not ok or user_dto is None:
            logger.error("❌ Emby 创建失败: user_id={} name={} err={}", user_id, name, err)
            return False, None, err or "Emby 创建失败"

        emby_id = str(user_dto.get("Id") or "")
        created_name = str(user_dto.get("Name") or name)

        # 持久化与绑定
        try:
            pwd_hash = hash_password(password)
            model = EmbyUserModel(emby_user_id=emby_id, name=created_name, user_dto=user_dto, password_hash=pwd_hash)
            history = EmbyUserHistoryModel(
                emby_user_id=emby_id,
                name=created_name,
                user_dto=user_dto,
                password_hash=pwd_hash,
                action="create",
            )
            session.add(model)
            session.add(history)

            if ext is None:
                ext = UserExtendModel(user_id=user_id, emby_user_id=emby_id)
                session.add(ext)
            else:
                ext.emby_user_id = emby_id

            await session.commit()
            logger.info("✅ Emby 用户创建并绑定成功: user_id={} emby_user_id={} name={}", user_id, emby_id, created_name)
        except SQLAlchemyError as e:
            logger.exception("❌ 写入数据库失败: user_id={} emby_user_id={} err={}", user_id, emby_id, str(e))
            return False, None, f"写入数据库失败: {e!s}"

        return True, {"name": created_name, "password": password}, None
    except Exception as e:
        logger.exception("❌ 注册流程系统异常: user_id={} err={}", user_id, str(e))
        return False, None, f"系统异常: {e!s}"
async def has_emby_account(session: AsyncSession, user_id: int) -> bool:
    """检查是否已绑定 Emby 账号

    功能说明:
    - 查询 `user_extend.emby_user_id` 是否存在

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID

    返回值:
    - bool: True 表示已绑定
    """
    res = await session.execute(select(UserExtendModel.emby_user_id).where(UserExtendModel.user_id == user_id))
    emby_id = res.scalar_one_or_none()
    return bool(emby_id)


async def get_user_and_extend(session: AsyncSession, user_id: int) -> tuple[UserModel | None, UserExtendModel | None]:
    """获取用户与扩展信息

    功能说明:
    - 同时查询 `users` 与 `user_extend` 模型，便于视图层构建信息

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID

    返回值:
    - tuple[UserModel | None, UserExtendModel | None]: 用户与扩展模型
    """
    user_res = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_res.scalar_one_or_none()
    ext_res = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user_id))
    ext = ext_res.scalar_one_or_none()
    return user, ext
