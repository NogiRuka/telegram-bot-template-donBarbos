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
        if copy_from_user_id:
            payload["CopyFromUserId"] = copy_from_user_id
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


class EmbyNotConfiguredError(Exception):
    """Emby 未配置异常

    功能说明:
    - 当未设置 EMBY_BASE_URL 或 EMBY_API_KEY 时抛出该异常

    输入参数:
    - 无

    返回值:
    - 无
    """


class EmbyFacade:
    """Emby 门面对象

    功能说明:
    - 提供 emb y.方法() 简洁调用格式, 内部按需构建 EmbyClient

    输入参数:
    - 无

    返回值:
    - 无
    """

    def _build_client(self) -> EmbyClient:
        """构建客户端

        功能说明:
        - 从配置读取 EMBY_BASE_URL 与 EMBY_API_KEY, 构建 EmbyClient

        输入参数:
        - 无

        返回值:
        - EmbyClient: 客户端实例
        """
        base_url = settings.get_emby_base_url()
        api_key = settings.get_emby_api_key()
        if not base_url or not api_key:
            msg = "Emby 未配置"
            raise EmbyNotConfiguredError(msg)
        return EmbyClient(base_url, api_key)

    async def get_users(self) -> list[dict[str, Any]]:
        """获取用户列表

        功能说明:
        - 直接调用 EmbyClient.get_users()

        输入参数:
        - 无

        返回值:
        - list[dict[str, Any]]: 用户对象列表
        """
        return await self._build_client().get_users()

    async def create_user(self, name: str, password: str | None = None) -> dict[str, Any]:
        """创建用户

        功能说明:
        - 直接调用 EmbyClient.create_user(), 若配置了模板用户ID则自动复制策略与配置

        输入参数:
        - name: 用户名
        - password: 密码, 可为 None

        返回值:
        - dict[str, Any]: 创建结果
        """
        template_id = settings.get_emby_template_user_id()
        return await self._build_client().create_user(
            name=name,
            password=password,
            copy_from_user_id=template_id,
            user_copy_options=["UserPolicy", "UserConfiguration"] if template_id else None,
        )

    async def delete_user(self, user_id: str) -> Any:
        """删除用户

        功能说明:
        - 直接调用 EmbyClient.delete_user()

        输入参数:
        - user_id: 用户ID

        返回值:
        - Any: 删除结果
        """
        return await self._build_client().delete_user(user_id)


# 简洁调用对象: emb y.方法()
emby = EmbyFacade()
