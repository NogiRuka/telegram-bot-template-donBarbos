from __future__ import annotations
from typing import Any, cast

from bot.core.config import settings
from bot.utils.http import HttpClient


class EmbyClient:
    """Emby API 客户端

    功能说明:
    - 封装 Emby 的常用接口, 依赖 `HttpClient` 进行请求

    输入参数:
    - base_url: Emby 服务地址, 如 `https://your-emby.com`
    - api_key: Emby API Key, 通过 `X-Emby-Token` 传递

    返回值:
    - 无
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self.http = HttpClient(base_url, api_key, base_path="/emby")

    async def get_users(
        self,
        is_hidden: bool | None = None,
        is_disabled: bool | None = None,
        start_index: int | None = None,
        limit: int | None = None,
        name_starts_with_or_greater: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """分页获取用户列表

        功能说明:
        - 调用 `GET /Users/Query` 返回 `Items` 与 `TotalRecordCount`

        输入参数:
        - is_hidden: 过滤 IsHidden
        - is_disabled: 过滤 IsDisabled
        - start_index: 起始索引
        - limit: 数量上限
        - name_starts_with_or_greater: 名称前缀过滤
        - sort_order: 排序 Ascending/Descending

        返回值:
        - tuple[list[dict[str, Any]], int]: (本页 Items, 总记录数)
        """
        params: dict[str, Any] = {}
        if is_hidden is not None:
            params["IsHidden"] = is_hidden
        if is_disabled is not None:
            params["IsDisabled"] = is_disabled
        if start_index is not None:
            params["StartIndex"] = int(start_index)
        if limit is not None:
            params["Limit"] = int(limit)
        if name_starts_with_or_greater:
            params["NameStartsWithOrGreater"] = str(name_starts_with_or_greater)
        if sort_order:
            params["SortOrder"] = str(sort_order)

        data = await self.http.request("GET", "/Users/Query", params=params)
        if isinstance(data, dict):
            items = data.get("Items")
            total = int(data.get("TotalRecordCount", 0))
            items_list = list(items) if isinstance(items, list) else []
            return items_list, total
        items_list = list(data or [])
        return items_list, len(items_list)

    async def create_user(
        self,
        name: str,
        password: str | None = None,
        copy_from_user_id: str | None = None,
        user_copy_options: list[str] | None = None,
    ) -> dict[str, Any]:
        """创建用户

        功能说明:
        - 调用 `POST /Users/New` 创建新用户
        - 支持模板用户复制: `CopyFromUserId` 与 `UserCopyOptions`
        - 若未传入 `copy_from_user_id`, 自动使用配置 `EMBY_TEMPLATE_USER_ID`

        输入参数:
        - name: 用户名
        - password: 密码, 可为 None
        - copy_from_user_id: 模板用户ID, 可为 None
        - user_copy_options: 复制选项, 可为 None; 常用值: ["UserPolicy", "UserConfiguration"]

        返回值:
        - dict[str, Any]: 创建结果
        """
        payload: dict[str, Any] = {"Name": name}
        if password:
            payload["Password"] = password
        template_id = copy_from_user_id or settings.get_emby_template_user_id()
        if template_id:
            payload["CopyFromUserId"] = template_id
        if user_copy_options:
            payload["UserCopyOptions"] = list(user_copy_options)
        return cast("dict[str, Any]", await self.http.request("POST", "/Users/New", json=payload))

    async def delete_user(self, user_id: str) -> Any:
        """删除用户

        功能说明:
        - 调用 `DELETE /Users/{user_id}` 删除指定用户

        输入参数:
        - user_id: 用户ID

        返回值:
        - Any: 删除结果(可能为空)
        """
        return await self.http.request("DELETE", f"/Users/{user_id}")


# 注意: 统一由服务层 `bot/services/emby_service.py:get_client` 负责从配置构建客户端
