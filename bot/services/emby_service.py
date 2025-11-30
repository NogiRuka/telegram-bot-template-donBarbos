from __future__ import annotations
from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import select

from bot.core.config import settings
from bot.core.emby import EmbyClient
from bot.database.models.emby_user import EmbyUserModel

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
    - sort_order: 排序，`Ascending` 或 `Descending`

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


async def create_user(name: str, password: str | None = None, copy_from_user_id: str | None = None) -> tuple[bool, dict[str, Any] | None, str | None]:
    """创建 Emby 用户

    功能说明:
    - 使用客户端调用 `POST /Users/New` 创建用户

    输入参数:
    - name: 用户名
    - password: 密码, 可为 None
    - copy_from_user_id: 模板用户ID, 可为 None

    返回值:
    - tuple[bool, dict[str, Any] | None, str | None]: (是否成功, 成功结果, 失败原因)
    """
    client = get_client()
    if client is None:
        return False, None, "未配置 Emby 连接信息"
    try:
        data = await client.create_user(name=name, password=password, copy_from_user_id=copy_from_user_id)
        return True, data, None
    except Exception as e:
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
        return True, res, None
    except Exception as e:
        return False, None, str(e)


async def save_all_emby_users(session: AsyncSession) -> tuple[int, int]:
    """保存所有 Emby 用户到数据库

    功能说明:
    - 调用 `GET /Users/Query` 获取所有用户(分页拉取), 并将结果同步到 `emby_users` 表
    - 已存在的记录执行更新(覆盖 `name` 与 `user_dto`), 不存在的记录执行插入

    输入参数:
    - session: 异步数据库会话

    返回值:
    - tuple[int, int]: (插入数量, 更新数量)
    """
    client = get_client()
    if client is None:
        logger.warning("未配置 Emby 连接信息, 跳过用户同步")
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
            logger.info("Emby 返回空用户列表, 无数据可同步")
            return 0, 0

        ids: list[str] = []
        for it in all_items:
            v = it.get("Id")
            if v is None:
                continue
            ids.append(str(v))

        existing_map: dict[str, EmbyUserModel] = {}
        if ids:
            res = await session.execute(select(EmbyUserModel).where(EmbyUserModel.emby_user_id.in_(ids)))
            existing = res.scalars().all()
            existing_map = {m.emby_user_id: m for m in existing}

        for it in all_items:
            eid_raw = it.get("Id")
            if eid_raw is None:
                continue
            eid = str(eid_raw)
            name = str(it.get("Name") or "")
            model = existing_map.get(eid)
            if model is None:
                session.add(EmbyUserModel(emby_user_id=eid, name=name, user_dto=it))
                inserted += 1
            else:
                model.name = name or model.name
                model.user_dto = it
                updated += 1

        await session.commit()
        logger.info("Emby 用户同步完成: 插入 {}, 更新 {}", inserted, updated)
        return inserted, updated
    except Exception as e:
        logger.error("Emby 用户同步失败: {}", str(e))
        with logger.catch():
            await session.rollback()
        return 0, 0
