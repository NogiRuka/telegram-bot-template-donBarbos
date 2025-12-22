from __future__ import annotations
import copy
import json
from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import select

from bot.core.config import settings
from bot.database.models.emby_device import EmbyDeviceModel
from bot.database.models.emby_user import EmbyUserModel
from bot.database.models.emby_user_history import EmbyUserHistoryModel
from bot.utils.datetime import now, parse_iso_datetime
from bot.utils.emby import get_emby_client
from bot.utils.http import HttpRequestError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession





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
    client = get_emby_client()
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
    client = get_emby_client()
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




async def get_item_details(item_id: str) -> dict[str, Any] | None:
    """获取 Emby 项目详情

    功能说明:
    - 使用模板用户ID调用 API 获取项目详情 (Path, Overview, ProviderIds 等)

    输入参数:
    - item_id: 项目ID (WebHook 载荷中的 Item.Id)

    返回值:
    - dict | None: 项目详情字典, 失败返回 None
    """
    client = get_emby_client()
    if client is None:
        return None

    # 使用模板用户ID作为查看者，确保能看到媒体库内容
    # 如果未配置模板用户，可能导致无权限查看或返回信息不全
    user_id = settings.get_emby_template_user_id()

    try:
        # 使用 get_items 批量查询接口，以便指定需要的 Fields
        # ids 为必填，user_id 为可选
        items, _ = await client.get_items(
            ids=[item_id],
            user_id=user_id,
            limit=1,
            recursive=True,
        )
        if items:
            return items[0]

        logger.warning(f"⚠️ 未找到 Emby 项目: {item_id} (可能是权限问题或项目已删除)")
        return None
    except Exception as e:
        logger.warning(f"❌ 获取项目详情失败: {item_id} -> {e}")
        return None


async def fetch_and_save_item_details(session: AsyncSession, item_ids: list[str]) -> dict[str, bool]:
    """批量从 Emby 获取项目详情并存入 emby_items 表

    功能说明:
    - 批量调用 Emby API 获取详细信息
    - 逐个构造 EmbyItemModel 并保存
    - 如果已存在则更新

    输入参数:
    - session: 数据库会话
    - item_ids: Emby Item ID 列表

    返回值:
    - dict[str, bool]: 结果映射 {item_id: success}
    """
    from sqlalchemy import func

    from bot.database.models.emby_item import EmbyItemModel
    from bot.database.models.notification import NotificationModel

    if not item_ids:
        return {}

    client = get_emby_client()
    if client is None:
        logger.warning("⚠️ 未配置 Emby 连接信息")
        return dict.fromkeys(item_ids, False)

    results = dict.fromkeys(item_ids, False)

    try:
        # 批量获取详情
        # 注意: get_items 接收 list[str]
        # Emby API 可能对 URL 长度有限制，如果 ids 太多可能需要分批
        # 这里假设 ids 数量适中 (例如几百个以内通常没问题，POST 查询可能更稳但 Emby API 这里是 GET)
        # 如果数量极大，建议上层分批调用
        logger.debug(f"🔍 正在批量查询 Emby 项目, IDs: {item_ids}")
        items, total = await client.get_items(
            ids=item_ids
        )
        logger.debug(f"🔙 Emby 接口返回: {total} 个项目, 实际数据: {len(items)} 条")
        if items:
            logger.debug(f"📦 第一条数据示例 (ID: {items[0].get('Id')}): Name={items[0].get('Name')}")
        else:
            logger.warning(f"⚠️ Emby 接口返回为空! 请求 IDs: {item_ids}")

        # 建立 item_id -> item_data 的映射
        items_map = {str(item.get("Id")): item for item in items}

        # 批量查询现有记录
        existing_stmt = select(EmbyItemModel).where(EmbyItemModel.id.in_(item_ids))
        existing_res = await session.execute(existing_stmt)
        existing_models = {m.id: m for m in existing_res.scalars().all()}

        for item_id in item_ids:
            item_details = items_map.get(item_id)
            if not item_details:
                logger.warning(f"⚠️ 未找到 Emby 项目: {item_id}")
                continue

            try:
                name = item_details.get("Name")
                date_created = str(parse_iso_datetime(item_details.get("DateCreated")))
                overview = item_details.get("Overview")
                item_type = item_details.get("Type")
                path = item_details.get("Path")
                people = item_details.get("People")
                tag_items = item_details.get("TagItems")
                image_tags = item_details.get("ImageTags")

                # 状态字段 (主要用于Series类型)
                status = item_details.get("Status")

                # 剧集进度字段 (仅Series类型有效)
                current_season = None
                current_episode = None
                episode_data = None
                if item_type == "Series":
                    # 获取剧集详情数据
                    try:
                        episodes, total_episodes = await client.get_series_episodes(
                            series_id=item_id
                        )
                        if episodes:
                            episode_data = {
                                "Items": episodes,
                                "TotalRecordCount": total_episodes
                            }
                            logger.debug(f"📺 Series {item_id}——{name} 获取剧集详情: {total_episodes} 集")

                            # 分析剧集数据，找出最新的季和集
                            max_season = 0
                            max_episode_in_season = {}

                            for episode in episodes:
                                if episode.get("Type") == "Episode":
                                    season_num = episode.get("ParentIndexNumber")
                                    episode_num = episode.get("IndexNumber")

                                    if season_num is not None and episode_num is not None:
                                        # 更新最大季号
                                        max_season = max(max_season, season_num)

                                        # 记录每季的最大集号
                                        season_key = season_num
                                        if season_key not in max_episode_in_season:
                                            max_episode_in_season[season_key] = 0
                                        max_episode_in_season[season_key] = max(max_episode_in_season[season_key], episode_num)

                            # 设置当前进度为最新季的最后一集
                            if max_season > 0 and max_season in max_episode_in_season:
                                current_season = max_season
                                current_episode = max_episode_in_season[max_season]
                                logger.debug(f"📺 Series {item_id}——{name} 进度更新: 第{current_season}季第{current_episode}集")
                        else:
                            logger.warning(f"⚠️ Series {item_id}——{name} 未获取到剧集详情")
                    except Exception as e:
                        logger.error(f"❌ 获取剧集详情失败: {item_id}——{name} -> {e}")
                        episode_data = None

                        # 如果获取剧集详情失败，回退到原来的通知表查询方式
                        series_stmt = select(
                            func.max(NotificationModel.season_number).label("max_season"),
                            func.max(NotificationModel.episode_number).label("max_episode")
                        ).where(
                            NotificationModel.series_id == item_id,
                            NotificationModel.season_number.is_not(None),
                            NotificationModel.episode_number.is_not(None)
                        )
                        series_result = await session.execute(series_stmt)
                        series_data = series_result.one_or_none()
                        if series_data and series_data.max_season is not None:
                            current_season = series_data.max_season
                            current_episode = series_data.max_episode
                            logger.debug(f"📺 Series {item_id} 最新进度(回退模式): 第{current_season}季第{current_episode}集")

                existing = existing_models.get(item_id)
                if existing:
                    existing.name = name
                    existing.date_created = date_created
                    existing.overview = overview
                    existing.type = item_type
                    existing.path = path
                    existing.status = status
                    existing.current_season = current_season
                    existing.current_episode = current_episode
                    existing.people = people
                    existing.tag_items = tag_items
                    existing.image_tags = image_tags
                    existing.original_data = item_details
                    existing.episode_data = episode_data
                    logger.debug(f"🔄 更新 Emby Item: {name} ({item_id})")
                else:
                    model = EmbyItemModel(
                        id=item_id,
                        name=name,
                        date_created=date_created,
                        overview=overview,
                        type=item_type,
                        path=path,
                        status=status,
                        current_season=current_season,
                        current_episode=current_episode,
                        people=people,
                        tag_items=tag_items,
                        image_tags=image_tags,
                        original_data=item_details,
                        episode_data=episode_data
                    )
                    session.add(model)
                    logger.debug(f"✅ 新增 Emby Item: {name} ({item_id})")

                results[item_id] = True
            except Exception as e:
                logger.error(f"❌ 保存 Emby Item 失败: {item_id} -> {e}")
                results[item_id] = False

    except Exception as e:
        logger.error(f"❌ 批量获取项目详情失败: {e}")
        # 所有都失败
        return results

    return results


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
    client = get_emby_client()
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


async def save_all_emby_devices(session: AsyncSession) -> int:
    """保存所有 Emby 设备到数据库

    功能说明:
    - 调用 `GET /Devices` 获取所有设备
    - 同步到 `emby_devices` 表
    - 若存在则更新，不存在则插入

    输入参数:
    - session: 数据库会话

    返回值:
    - int: 同步的设备数量
    """
    client = get_emby_client()
    if client is None:
        logger.warning("⚠️ 未配置 Emby 连接信息, 跳过设备同步")
        return 0

    try:
        devices, total = await client.get_devices()
        if not devices:
            logger.info("📭 Emby 返回空设备列表")
            return 0
            
        logger.info(f"🔄 开始同步 Emby 设备, 共 {len(devices)} 个")
        
        # 批量查询现有记录
        device_ids = [str(d.get("Id")) for d in devices if d.get("Id")]
        if not device_ids:
             return 0

        existing_stmt = select(EmbyDeviceModel).where(EmbyDeviceModel.emby_device_id.in_(device_ids))
        existing_res = await session.execute(existing_stmt)
        existing_models = {m.emby_device_id: m for m in existing_res.scalars().all()}
        
        count = 0
        for device_data in devices:
            emby_device_id = str(device_data.get("Id"))
            if not emby_device_id:
                continue
                
            reported_id = device_data.get("ReportedDeviceId")
            name = device_data.get("Name")
            last_user_name = device_data.get("LastUserName")
            app_name = device_data.get("AppName")
            app_version = device_data.get("AppVersion")
            last_user_id = device_data.get("LastUserId")
            icon_url = device_data.get("IconUrl")
            ip_address = device_data.get("IpAddress")
            
            date_last_activity_str = device_data.get("DateLastActivity")
            date_last_activity = parse_iso_datetime(date_last_activity_str) if date_last_activity_str else None
            
            model = existing_models.get(emby_device_id)
            if model:
                # Update
                model.reported_device_id = reported_id
                model.name = name
                model.last_user_name = last_user_name
                model.app_name = app_name
                model.app_version = app_version
                model.last_user_id = last_user_id
                model.date_last_activity = date_last_activity
                model.icon_url = icon_url
                model.ip_address = ip_address
                model.raw_data = device_data
            else:
                # Insert
                model = EmbyDeviceModel(
                    emby_device_id=emby_device_id,
                    reported_device_id=reported_id,
                    name=name,
                    last_user_name=last_user_name,
                    app_name=app_name,
                    app_version=app_version,
                    last_user_id=last_user_id,
                    date_last_activity=date_last_activity,
                    icon_url=icon_url,
                    ip_address=ip_address,
                    raw_data=device_data
                )
                session.add(model)
            count += 1
            
        await session.commit()
        logger.info(f"✅ Emby 设备同步完成: {count} 个")
        return count
        
    except Exception as e:
        logger.error(f"❌ Emby 设备同步失败: {e}")
        await session.rollback()
        return 0


async def cleanup_devices_by_policy(session: AsyncSession) -> int:
    """根据用户 Policy 清理设备

    功能说明:
    - 遍历所有 Emby 用户
    - 检查 Policy 中的 EnableAllDevices 和 EnabledDevices
    - 如果 EnableAllDevices 为 False，则软删除不在 EnabledDevices 中的设备
    - 仅处理属于该用户(last_user_id)的设备

    输入参数:
    - session: 数据库会话

    返回值:
    - int: 被软删除的设备数量
    """
    try:
        # 1. 获取所有用户
        stmt = select(EmbyUserModel)
        result = await session.execute(stmt)
        users = result.scalars().all()

        deleted_count = 0

        for user in users:
            if not user.user_dto:
                continue
                
            policy = user.user_dto.get("Policy", {})
            enable_all_devices = policy.get("EnableAllDevices", True)
            enabled_devices = set(policy.get("EnabledDevices", []))

            # 如果允许所有设备，则不需要清理
            if enable_all_devices:
                continue

            # 2. 查找该用户的所有未删除设备
            # 注意: 仅处理 last_user_id 匹配的设备
            device_stmt = select(EmbyDeviceModel).where(
                EmbyDeviceModel.last_user_id == user.emby_user_id,
                EmbyDeviceModel.is_deleted == False
            )
            device_res = await session.execute(device_stmt)
            user_devices = device_res.scalars().all()

            for device in user_devices:
                # 检查 reported_device_id 是否在允许列表中
                # 注意: 如果 device.reported_device_id 为空，也视为不在允许列表中
                if device.reported_device_id not in enabled_devices:
                    device.is_deleted = True
                    device.deleted_at = now()
                    device.deleted_by = 0  # 0 表示系统
                    device.remark = f"Policy限制: 不在 EnabledDevices 中 (EnableAllDevices=False)"
                    session.add(device)
                    deleted_count += 1
                    logger.info(f"🗑️ 软删除设备: User={user.name}, Device={device.name or 'Unknown'} ({device.reported_device_id})")

        if deleted_count > 0:
            await session.commit()
            logger.info(f"✅ 根据 Policy 清理了 {deleted_count} 个设备")
        
        return deleted_count

    except Exception as e:
        logger.error(f"❌ 设备清理失败: {e}")
        return 0
