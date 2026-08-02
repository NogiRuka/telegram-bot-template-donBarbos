from __future__ import annotations
from typing import Any, cast

from bot.core.config import settings
from bot.utils.http import HttpClient
from loguru import logger


class EmbyClient:
    """Emby API 客户端，封装常用接口，依赖 HttpClient 发起请求。"""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.http = HttpClient(
            base_url, 
            headers={
                "X-Emby-Token": api_key,
            },
            base_path="/emby"
        )

    async def close(self) -> None:
        """关闭 HTTP 客户端资源。"""
        await self.http.close()

    # ------------------------------------------------------------------
    # 系统
    # ------------------------------------------------------------------

    async def get_system_info(self) -> dict[str, Any]:
        """获取 Emby 系统信息，可用于测试连接 (GET /System/Info)。"""
        data = await self.http.request("GET", "/System/Info")
        return cast("dict[str, Any]", data) if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # 用户管理
    # ------------------------------------------------------------------

    async def get_users(
        self,
        is_hidden: bool | None = None,
        is_disabled: bool | None = None,
        start_index: int | None = None,
        limit: int | None = None,
        name_starts_with_or_greater: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """分页获取用户列表 (GET /Users/Query)。"""
        params: dict[str, Any] = {}
        if is_hidden is not None:
            params["IsHidden"] = str(is_hidden).lower()
        if is_disabled is not None:
            params["IsDisabled"] = str(is_disabled).lower()
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
        copy_from_user_id: str | None = None,
        user_copy_options: list[str] | None = None,
    ) -> dict[str, Any]:
        """创建用户，支持模板复制 (POST /Users/New)。"""
        payload: dict[str, Any] = {"Name": name}
        template_id = copy_from_user_id or settings.get_emby_template_user_id()
        if template_id:
            payload["CopyFromUserId"] = template_id
        if user_copy_options:
            payload["UserCopyOptions"] = list(user_copy_options)
        return cast("dict[str, Any]", await self.http.request("POST", "/Users/New", json=payload))

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """获取用户详情 (GET /Users/{Id})。"""
        data = await self.http.request("GET", f"/Users/{user_id}")
        return cast("dict[str, Any]", data) if isinstance(data, dict) else {}

    async def delete_user(self, user_id: str) -> Any:
        """删除用户 (DELETE /Users/{Id})。"""
        return await self.http.request("DELETE", f"/Users/{user_id}")

    async def upload_user_image(
        self,
        user_id: str,
        image_data: str,
        image_type: str = "Primary",
    ) -> Any:
        """上传用户图片，image_data 需为 Base64 字符串 (POST /Users/{Id}/Images/{Type})。"""
        headers = {"Content-Type": "image/jpeg"}
        return await self.http.request(
            "POST",
            f"/Users/{user_id}/Images/{image_type}",
            data=image_data,
            headers=headers,
        )

    async def update_user_password(
        self, user_id: str, new_password: str, reset_password: bool = False
    ) -> Any:
        """更新用户密码 (POST /Users/{Id}/Password)。"""
        payload = {
            "Id": user_id,
            "NewPw": new_password,
            "ResetPassword": reset_password,
        }
        return await self.http.request("POST", f"/Users/{user_id}/Password", json=payload)

    async def disable_user(self, user_id: str) -> bool:
        """禁用用户：置 Policy.IsDisabled=True。"""
        policy = await self.get_user_policy(user_id)
        if policy:
            policy["IsDisabled"] = True
            await self.update_user_policy(user_id, policy)
            return True
        return False

    async def enable_user(self, user_id: str) -> bool:
        """启用用户：置 Policy.IsDisabled=False。"""
        policy = await self.get_user_policy(user_id)
        if policy:
            policy["IsDisabled"] = False
            await self.update_user_policy(user_id, policy)
            return True
        return False

    # ------------------------------------------------------------------
    # 用户配置与策略
    # ------------------------------------------------------------------

    async def get_user_configuration(self, user_id: str) -> dict[str, Any]:
        """获取用户 Configuration。"""
        user = await self.get_user(user_id)
        return user.get("Configuration", {})

    async def get_user_policy(self, user_id: str) -> dict[str, Any]:
        """获取用户 Policy。"""
        user = await self.get_user(user_id)
        return user.get("Policy", {})

    async def update_user_configuration(
        self, user_id: str, configuration: dict[str, Any]
    ) -> Any:
        """更新用户 Configuration (POST /Users/{Id}/Configuration)。"""
        return await self.http.request(
            "POST", f"/Users/{user_id}/Configuration", json=configuration
        )

    async def update_user_policy(self, user_id: str, policy: dict[str, Any]) -> Any:
        """更新用户 Policy (POST /Users/{Id}/Policy)。"""
        return await self.http.request("POST", f"/Users/{user_id}/Policy", json=policy)

    # ------------------------------------------------------------------
    # 项目查询与管理
    # ------------------------------------------------------------------

    async def get_item(self, user_id: str, item_id: str) -> dict[str, Any]:
        """获取项目详情 (GET /Users/{UserId}/Items/{Id})。"""
        data = await self.http.request("GET", f"/Users/{user_id}/Items/{item_id}")
        if isinstance(data, dict):
            logger.debug(
                "Emby get_item response: data={}",
                data,
            )
            return cast("dict[str, Any]", data)
        logger.debug(
            "Emby get_item response is not dict: user_id={} item_id={} type={} value={}",
            user_id,
            item_id,
            type(data).__name__,
            data,
        )
        return {}

    async def get_items(
        self,
        ids: list[str],
        user_id: str | None = None,
        fields: list[str] | None = None,
        recursive: bool = True,
        limit: int | None = None,
        start_index: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        parent_id: str | None = None,
        filters: list[str] | None = None,
        include_item_types: list[str] | None = None,
        media_types: list[str] | None = None,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        """通用项目查询 (GET /Items)，支持批量 ids 与丰富过滤。"""
        params = kwargs.copy()
        if user_id:
            params["UserId"] = user_id

        params["Ids"] = ",".join(ids)

        # 未指定 fields 时请求关键元数据
        default_fields = [
            "DateCreated",
            "Tags",
            "Overview",
            "People",
            "Path",
            "Status",
            "SeriesName",
            "SeriesId",
            "IndexNumber",
            "ParentIndexNumber",
        ]
        if fields:
            params["Fields"] = ",".join(fields)
        else:
            params["Fields"] = ",".join(default_fields)

        if recursive:
            params["Recursive"] = "true"
        if limit is not None:
            params["Limit"] = int(limit)
        if start_index is not None:
            params["StartIndex"] = int(start_index)
        if sort_by:
            params["SortBy"] = sort_by
        if sort_order:
            params["SortOrder"] = sort_order
        if parent_id:
            params["ParentId"] = parent_id
        if filters:
            params["Filters"] = ",".join(filters)
        if include_item_types:
            params["IncludeItemTypes"] = ",".join(include_item_types)
        if media_types:
            params["MediaTypes"] = ",".join(media_types)

        data = await self.http.request("GET", "/Items", params=params)

        items: list[dict[str, Any]] = []
        total = 0
        if isinstance(data, dict):
            items = list(data.get("Items", []))
            total = int(data.get("TotalRecordCount", 0))
        elif isinstance(data, list):
            # 兼容直接返回列表的情况
            items = [x for x in data if isinstance(x, dict)]
            total = len(items)

        return items, total

    async def get_series_episodes(
        self,
        series_id: str,
        user_id: str | None = None,
        season: int | None = None,
        fields: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取剧集集列表 (GET /Shows/{series_id}/Episodes)。"""
        params: dict[str, Any] = {}
        if user_id:
            params["UserId"] = user_id
        if season is not None:
            params["Season"] = season
        if fields:
            params["Fields"] = ",".join(fields)

        data = await self.http.request("GET", f"/Shows/{series_id}/Episodes", params=params)

        items: list[dict[str, Any]] = []
        total = 0
        if isinstance(data, dict):
            items = list(data.get("Items", []))
            total = int(data.get("TotalRecordCount", 0))
        elif isinstance(data, list):
            # 兼容直接返回列表的情况
            items = [x for x in data if isinstance(x, dict)]
            total = len(items)

        return items, total

    async def update_item(self, item_id: str, item_data: dict[str, Any]) -> Any:
        """更新 Item 元数据，item_data 为完整 Item DTO (POST /Items/{ItemId})。"""
        return await self.http.request("POST", f"/Items/{item_id}", json=item_data)

    async def upload_item_image(
        self,
        item_id: str,
        image_data: str,
        image_type: str = "Primary",
    ) -> Any:
        """上传 Item 图片，image_data 需为 Base64 字符串 (POST /Items/{ItemId}/Images/{Type})。"""
        headers = {"Content-Type": "image/jpeg"}
        return await self.http.request(
            "POST",
            f"/Items/{item_id}/Images/{image_type}",
            data=image_data,
            headers=headers,
        )

    # ------------------------------------------------------------------
    # 会话与设备
    # ------------------------------------------------------------------

    async def get_sessions(
        self,
        controllable_by_user_id: str | None = None,
        device_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取会话列表 (GET /Sessions)。"""
        params: dict[str, Any] = {}
        if controllable_by_user_id:
            params["ControllableByUserId"] = str(controllable_by_user_id)
        if device_id:
            params["DeviceId"] = str(device_id)
        if session_id:
            params["Id"] = str(session_id)

        data = await self.http.request("GET", "/Sessions", params=params)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []

    async def send_session_message(
        self,
        session_id: str,
        header: str,
        text: str,
        timeout_ms: int | None = None,
    ) -> Any:
        """向客户端会话发送消息 (POST /Sessions/{Id}/Message)。"""
        params: dict[str, Any] = {"Header": header, "Text": text}
        if timeout_ms is not None:
            params["TimeoutMs"] = int(timeout_ms)

        return await self.http.request(
            "POST", f"/Sessions/{session_id}/Message", params=params
        )

    async def get_devices(
        self,
        sort_order: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取设备列表，仅管理员可用 (GET /Devices)。"""
        params: dict[str, Any] = {}
        if sort_order:
            params["SortOrder"] = str(sort_order)

        data = await self.http.request("GET", "/Devices", params=params)
        if isinstance(data, dict):
            items = data.get("Items")
            total = int(data.get("TotalRecordCount", 0))
            items_list = list(items) if isinstance(items, list) else []
            return items_list, total
        items_list = list(data or [])
        return items_list, len(items_list)
