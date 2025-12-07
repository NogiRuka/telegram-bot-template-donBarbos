from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import select

from bot.core.config import settings
from bot.core.emby import EmbyClient
from bot.database.models.emby_user import EmbyUserModel
from bot.database.models.emby_user_history import EmbyUserHistoryModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def get_client() -> EmbyClient | None:
    """获取 Emby 客户端

    功能说明:
    - 从配置中直接构建 `EmbyClient`, 任一配置缺失返回 None

    输入参数:
    - 无

    返回值:
    - EmbyClient | None: 客户端实例或 None
    """
    base_url = settings.get_emby_base_url()
    api_key = settings.get_emby_api_key()
    if not base_url or not api_key:
        return None
    return EmbyClient(base_url, api_key)


async def list_users(
    is_hidden: bool | None = None,
    is_disabled: bool | None = None,
    start_index: int | None = None,
    limit: int | None = None,
    name_starts_with_or_greater: str | None = None,
    sort_order: str | None = None,
) -> list[dict[str, Any]]:
    """列出 Emby 用户

    功能说明:
    - 使用客户端调用 `GET /Users/Query`

    输入参数:
    - is_hidden: 过滤隐藏
    - is_disabled: 过滤禁用
    - start_index: 起始索引
    - limit: 返回数量上限
    - name_starts_with_or_greater: 名称前缀过滤
    - sort_order: 排序, `Ascending` 或 `Descending`

    返回值:
    - list[dict[str, Any]]: 用户列表, 客户端缺失时返回空列表
    """
    client = get_client()
    if client is None:
        return []
    return await client.get_users(
        is_hidden=is_hidden,
        is_disabled=is_disabled,
        start_index=start_index,
        limit=limit,
        name_starts_with_or_greater=name_starts_with_or_greater,
        sort_order=sort_order,
    )


async def create_user(
    name: str,
    password: str | None = None,
    template_user_id: str | None = None,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """创建 Emby 用户（完整流程）

    功能说明:
    - 完整的用户创建流程:
      1. 调用 `POST /Users/New` 创建无密码用户
      2. 从模板用户获取 Configuration 和 Policy
      3. 更新新用户的 Configuration 和 Policy
      4. 设置用户密码

    输入参数:
    - name: 用户名
    - password: 密码, 可为 None（不设置密码）
    - template_user_id: 模板用户ID, 可为 None（使用配置中的默认模板）

    返回值:
    - tuple[bool, dict[str, Any] | None, str | None]: (是否成功, UserDto, 失败原因)
    """
    client = get_client()
    if client is None:
        return False, None, "未配置 Emby 连接信息"

    try:
        # Step 1: 创建无密码用户
        user_dto = await client.create_user(name=name)
        user_id = str(user_dto.get("Id") or "")
        if not user_id:
            return False, None, "创建用户失败: 未返回用户ID"

        # Step 2: 获取模板用户的 Configuration 和 Policy
        tid = template_user_id or settings.get_emby_template_user_id()
        if tid:
            try:
                template_user = await client.get_user(tid)
                template_config = template_user.get("Configuration")
                template_policy = template_user.get("Policy")

                # Step 3: 更新新用户的 Configuration 和 Policy
                if template_config and isinstance(template_config, dict):
                    await client.update_user_configuration(user_id, template_config)

                if template_policy and isinstance(template_policy, dict):
                    await client.update_user_policy(user_id, template_policy)
            except Exception as e:  # noqa: BLE001
                logger.warning("⚠️ 复制模板用户配置失败: {}", str(e))

        # Step 4: 设置密码
        if password:
            try:
                await client.update_user_password(user_id, password)
            except Exception as e:  # noqa: BLE001
                logger.warning("⚠️ 设置用户密码失败: {}", str(e))

        # 重新获取最新的用户信息
        try:
            user_dto = await client.get_user(user_id)
        except Exception:  # noqa: BLE001
            pass  # 使用创建时返回的 user_dto

        return True, user_dto, None

    except Exception as e:  # noqa: BLE001
        return False, None, str(e)


async def delete_user(user_id: str) -> tuple[bool, Any | None, str | None]:
    """删除 Emby 用户

    功能说明:
    - 使用客户端调用 `DELETE /Users/{user_id}` 删除用户

    输入参数:
    - user_id: 用户ID

    返回值:
    - tuple[bool, Any | None, str | None]: (是否成功, 结果, 失败原因)
    """
    client = get_client()
    if client is None:
        return False, None, "未配置 Emby 连接信息"
    try:
        res = await client.delete_user(user_id)
    except Exception as e:  # noqa: BLE001
        return False, None, str(e)
    else:
        return True, res, None


async def save_all_emby_users(session: AsyncSession) -> tuple[int, int]:
    """保存所有 Emby 用户到数据库

    功能说明:
    - 调用 `GET /Users/Query` 获取所有用户(分页拉取), 并将结果同步到 `emby_users` 表
    - 已存在的记录执行更新(覆盖 `name` 与 `user_dto` 及日期字段), 不存在的记录执行插入
    - 当 `emby_users` 的字段发生变化时, 写入一条 `emby_user_history` 更新记录

    输入参数:
    - session: 异步数据库会话

    返回值:
    - tuple[int, int]: (插入数量, 更新数量)
    """
    client = get_client()
    if client is None:
        logger.warning("⚠️ 未配置 Emby 连接信息, 跳过用户同步")
        return 0, 0

    inserted = 0
    updated = 0
    try:
        all_items: list[dict[str, Any]] = []
        start_index = 0
        page_limit = 200
        while True:
            items, total = await client.get_users(start_index=start_index, limit=page_limit)
            if not items:
                break
            all_items.extend(items)
            start_index += len(items)
            if len(all_items) >= total or len(items) < page_limit:
                break

        # 导入时间解析工具
        from bot.utils.datetime import parse_iso_datetime

        if not all_items:
            logger.info("📭 Emby 返回空用户列表, 无数据可同步")
            return 0, 0

        # 构建接口返回的用户ID集合和映射
        api_user_map: dict[str, dict[str, Any]] = {}
        for it in all_items:
            eid_raw = it.get("Id")
            if eid_raw is not None:
                api_user_map[str(eid_raw)] = it

        # 查询数据库中所有现有用户
        res = await session.execute(select(EmbyUserModel))
        existing_models = res.scalars().all()
        existing_map: dict[str, EmbyUserModel] = {m.emby_user_id: m for m in existing_models}

        deleted = 0

        # 1. 处理删除：数据库有但接口没有的用户
        for eid, model in existing_map.items():
            if eid not in api_user_map:
                # 软删除：写入历史表（标记 is_deleted），从主表删除
                import datetime as dt

                session.add(
                    EmbyUserHistoryModel(
                        emby_user_id=eid,
                        name=model.name,
                        user_dto=model.user_dto,
                        password_hash=model.password_hash,
                        action="delete",
                        date_created=model.date_created,
                        last_login_date=model.last_login_date,
                        last_activity_date=model.last_activity_date,
                        remark=model.remark,
                        created_at=model.created_at,
                        updated_at=model.updated_at,
                        is_deleted=model.is_deleted,
                        deleted_at=model.deleted_at,
                        created_by=model.created_by,
                        updated_by=model.updated_by,
                        deleted_by=model.deleted_by,
                    )
                )
                await session.delete(model)
                deleted += 1

        # 2. 处理新增和更新
        for eid, it in api_user_map.items():

            model = existing_map.get(eid)
            if model is None:
                name = str(it.get("Name") or "")
                date_created = parse_iso_datetime(it.get("DateCreated"))
                last_login_date = parse_iso_datetime(it.get("LastLoginDate"))
                last_activity_date = parse_iso_datetime(it.get("LastActivityDate"))

                # 新增
                session.add(
                    EmbyUserModel(
                        emby_user_id=eid,
                        name=name,
                        user_dto=it,
                        date_created=date_created,
                        last_login_date=last_login_date,
                        last_activity_date=last_activity_date,
                    )
                )
                inserted += 1
            else:
                # 更新：只比较 user_dto，有变化就写入历史表
                old_dto = model.user_dto
                new_dto = it

                if old_dto != new_dto:
                    name = str(it.get("Name") or "")
                    date_created = parse_iso_datetime(it.get("DateCreated"))
                    last_login_date = parse_iso_datetime(it.get("LastLoginDate"))
                    last_activity_date = parse_iso_datetime(it.get("LastActivityDate"))

                    # 检测具体哪些字段变化了
                    changed_fields: list[str] = []
                    old_name = model.name
                    old_dc = model.date_created
                    old_ll = model.last_login_date
                    old_la = model.last_activity_date
                    old_remark = model.remark
                    old_password_hash = model.password_hash
                    old_remark = model.remark

                    if name != old_name:
                        changed_fields.append(f"name: '{old_name}' -> '{name}'")
                    if date_created != old_dc:
                        changed_fields.append(f"date_created: '{old_dc}' -> '{date_created}'")
                    if last_login_date != old_ll:
                        changed_fields.append(f"last_login_date: '{old_ll}' -> '{last_login_date}'")
                    if last_activity_date != old_la:
                        changed_fields.append(f"last_activity_date: '{old_la}' -> '{last_activity_date}'")

                    # 生成备注
                    remark = "; ".join(changed_fields) if changed_fields else "user_dto 有其他字段变化"

                    # 保存旧数据到历史表
                    session.add(
                        EmbyUserHistoryModel(
                            emby_user_id=eid,
                            name=old_name,
                            user_dto=old_dto,
                            password_hash=old_password_hash,
                            action="update",
                            date_created=old_dc,
                            last_login_date=old_ll,
                            last_activity_date=old_la,
                            remark=old_remark,
                            created_at=model.created_at,
                            updated_at=model.updated_at,
                            is_deleted=model.is_deleted,
                            deleted_at=model.deleted_at,
                            created_by=model.created_by,
                            updated_by=model.updated_by,
                            deleted_by=model.deleted_by,
                        )
                    )
                    updated += 1
                    model.remark = remark

                    # 更新主表字段
                    model.name = name
                    model.user_dto = it
                    model.date_created = date_created
                    model.last_login_date = last_login_date
                    model.last_activity_date = last_activity_date

        await session.commit()
        logger.info("✅ Emby 用户同步完成: 插入 {}, 更新 {}, 删除 {}", inserted, updated, deleted)
        return inserted, updated
    except Exception as e:  # noqa: BLE001
        logger.error("❌ Emby 用户同步失败: {}", str(e))
        with logger.catch():
            await session.rollback()
        return 0, 0
