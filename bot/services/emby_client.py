from __future__ import annotations
from typing import Any

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
        self.http = HttpClient(base_url, api_key)

    async def get_users(self) -> list[dict[str, Any]]:
        """获取用户列表

        功能说明:
        - 调用 `GET /Users` 获取所有 Emby 用户

        输入参数:
        - 无

        返回值:
        - list[dict[str, Any]]: 用户对象列表
        """
        data = await self.http.request("GET", "/Users")
        return list(data or [])

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
            opts = user_copy_options or ["UserPolicy", "UserConfiguration"]
            payload["UserCopyOptions"] = opts
        return await self.http.request("POST", "/Users/New", json=payload)

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


def get_emby_client_from_settings() -> EmbyClient | None:
    """从配置构建 EmbyClient

    功能说明:
    - 读取 `EMBY_BASE_URL` 与 `EMBY_API_KEY`, 构建 `EmbyClient`
    - 任一缺失则返回 None

    输入参数:
    - 无

    返回值:
    - EmbyClient | None: 成功返回客户端实例, 缺少配置返回 None
    """
    base_url = settings.get_emby_base_url()
    api_key = settings.get_emby_api_key()
    if not base_url or not api_key:
        return None
    return EmbyClient(base_url, api_key)

