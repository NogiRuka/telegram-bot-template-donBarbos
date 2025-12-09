from __future__ import annotations
import json
from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import select

from bot.core.config import settings
from bot.core.emby import EmbyClient
from bot.database.models.emby_user import EmbyUserModel
from bot.database.models.emby_user_history import EmbyUserHistoryModel
from bot.utils.datetime import now, parse_iso_datetime
from bot.utils.http import HttpRequestError

import copy

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

    except HttpRequestError as e:
        # 优先返回响应体中的错误详情(通常是 Emby 的具体报错信息)
        err_msg = e.body.strip() if e.body else str(e)
        logger.warning(f"❌ Emby 创建用户 API 错误: {err_msg}")
        return False, None, err_msg

    except Exception as e:  # noqa: BLE001
        return False, None, str(e)


async def sync_all_users_configuration(
    exclude_user_ids: list[str] | None = None,
    specific_user_ids: list[str] | None = None,
) -> tuple[int, int]:
    """批量同步所有用户的 Configuration 和 Policy 为模板用户配置

    功能说明:
    - 遍历所有 Emby 用户
    - 将 Configuration 和 Policy 更新为模板用户的一致配置
    - 支持 exclude_user_ids 排除特定用户
    - 支持 specific_user_ids 仅同步特定用户 (优先级高于 exclude)

    输入参数:
    - exclude_user_ids: 要跳过的用户ID列表
    - specific_user_ids: 仅同步的用户ID列表

    返回值:
    - tuple[int, int]: (成功更新数量, 失败数量)
    """
    client = get_client()
    if client is None:
        logger.warning("⚠️ 未配置 Emby 连接信息, 无法同步配置")
        return 0, 0

    tid = settings.get_emby_template_user_id()
    if not tid:
        logger.warning("⚠️ 未配置 Emby 模板用户ID (EMBY_TEMPLATE_USER_ID), 无法同步配置")
        return 0, 0

    # 获取模板用户详情
    try:
        template_user = await client.get_user(tid)
    except Exception as e:
        logger.error(f"❌ 获取模板用户({tid})失败: {e}")
        return 0, 0

    template_config = template_user.get("Configuration")
    template_policy = template_user.get("Policy")

    if not isinstance(template_config, dict) or not isinstance(template_policy, dict):
        logger.error("❌ 模板用户的 Configuration 或 Policy 格式错误")
        return 0, 0

    # 获取目标用户列表
    all_users = []
    if specific_user_ids:
        # 指定了用户ID列表，直接构造用户对象列表（需获取Name以便日志显示）
        for uid in specific_user_ids:
            try:
                # 尝试获取用户信息以获得正确的 Name
                u = await client.get_user(uid)
                if u:
                    all_users.append(u)
                else:
                    # 获取失败或为空，构造一个只有 ID 的对象
                    all_users.append({"Id": uid, "Name": "Unknown"})
            except Exception:
                # 获取失败，构造一个只有 ID 的对象
                all_users.append({"Id": uid, "Name": "Unknown"})
    else:
        # 未指定用户，拉取所有用户
        try:
            start_index = 0
            page_limit = 200
            while True:
                items, total = await client.get_users(start_index=start_index, limit=page_limit)
                if not items:
                    break
                all_users.extend(items)
                start_index += len(items)
                if len(all_users) >= total or len(items) < page_limit:
                    break
        except Exception as e:
            logger.error(f"❌ 获取用户列表失败: {e}")
            return 0, 0

    # 准备排除列表
    skips = set(exclude_user_ids or [])
    skips.add(tid)  # 排除模板用户自己

    success_count = 0
    fail_count = 0

    logger.info(f"🔄 开始批量同步 Emby 用户配置, 模板用户: {tid}, 目标用户数: {len(all_users)}")

    for user in all_users:
        uid = user.get("Id")
        name = user.get("Name")
        if not uid:
            continue

        if uid in skips and not specific_user_ids:
             # 只有在非指定模式下才检查排除列表
             # 如果明确指定了 specific_user_ids，则即使在 exclude 中也应该执行（或者看逻辑，通常 specific 优先级更高）
             # 这里保持 specific 优先级更高，不检查 skip
             pass
        elif uid in skips:
             logger.debug(f"⏭️ 跳过用户: {name} ({uid})")
             continue

        try:
            # 更新 Configuration
            await client.update_user_configuration(uid, template_config)
            # 更新 Policy
            await client.update_user_policy(uid, template_policy)
            logger.debug(f"✅ 已更新用户配置: {name} ({uid})")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ 更新用户配置失败: {name} ({uid}) -> {e}")
            fail_count += 1

    logger.info(f"✅ 批量同步完成: 成功 {success_count}, 失败 {fail_count}")
    return success_count, fail_count


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
                # 软删除：写入简单历史快照，从主表删除
                session.add(
                    EmbyUserHistoryModel(
                        emby_user_id=eid,
                        name=model.name,
                        password_hash=model.password_hash,
                        date_created=model.date_created,
                        last_login_date=model.last_login_date,
                        last_activity_date=model.last_activity_date,
                        user_dto=model.user_dto,
                        action="delete",
                        created_at=model.created_at,
                        updated_at=model.updated_at,
                        created_by=model.created_by,
                        updated_by=model.updated_by,
                        is_deleted=True,
                        deleted_at=now(),
                        deleted_by=model.deleted_by,
                        remark=model.remark,
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
                # 必须深拷贝旧数据，防止引用被后续修改污染，导致历史表存入新数据
                old_dto = copy.deepcopy(model.user_dto)
                new_dto = it

                def _canon_json(obj: Any) -> str:
                    """生成规范化 JSON 字符串用于比较

                    功能说明:
                    - 将 Python 对象转换为排序键且紧凑的 JSON 字符串
                    - 解决字典键顺序、数字表现形式等导致的误判

                    输入参数:
                    - obj: 任意可 JSON 序列化的对象

                    返回值:
                    - str: 规范化后的 JSON 字符串
                    """
                    try:
                        return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                    except Exception:  # noqa: BLE001
                        return str(obj)

                if _canon_json(old_dto) != _canon_json(new_dto):
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
                        changed_fields.append(f"name 从 {old_name} 更新为 {name}")
                    if date_created != old_dc:
                        changed_fields.append(f"date_created 从 {old_dc} 更新为 {date_created}")
                    if last_login_date != old_ll:
                        changed_fields.append(f"last_login_date 从 {old_ll} 更新为 {last_login_date}")
                    if last_activity_date != old_la:
                        changed_fields.append(f"last_activity_date 从 {old_la} 更新为 {last_activity_date}")

                    # 生成备注
                    remark = "; ".join(changed_fields) if changed_fields else "user_dto 有其他字段变化"

                    # 保存旧数据到历史表
                    session.add(
                        EmbyUserHistoryModel(
                            emby_user_id=eid,
                            name=old_name,
                            password_hash=old_password_hash,
                            date_created=model.date_created,
                            last_login_date=model.last_login_date,
                            last_activity_date=model.last_activity_date,
                            user_dto=old_dto,
                            action="update",
                            created_at=model.created_at,
                            updated_at=model.updated_at,
                            created_by=model.created_by,
                            updated_by=model.updated_by,
                            is_deleted=model.is_deleted,
                            deleted_at=model.deleted_at,
                            deleted_by=model.deleted_by,
                            remark=old_remark,
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
