from __future__ import annotations
from typing import Any

from bot.services.emby_client import EmbyClient


class EmbyUserService:
    """Emby 用户服务

    功能说明:
    - 基于 `EmbyClient` 提供用户管理的业务封装

    输入参数:
    - client: `EmbyClient` 实例

    返回值:
    - 无
    """

    def __init__(self, client: EmbyClient) -> None:
        self.client = client

    async def list_users(self) -> list[dict[str, Any]]:
        """列出所有用户

        功能说明:
        - 返回 Emby 用户列表, 便于 handler 层展示

        输入参数:
        - 无

        返回值:
        - list[dict[str, Any]]: 用户对象列表
        """
        return await self.client.get_users()

    async def add_user(self, name: str, password: str) -> dict[str, Any]:
        """新增用户

        功能说明:
        - 创建一个新的 Emby 用户

        输入参数:
        - name: 用户名
        - password: 密码

        返回值:
        - dict[str, Any]: 创建结果
        """
        return await self.client.create_user(name=name, password=password)

    async def remove_user(self, user_id: str) -> Any:
        """删除用户

        功能说明:
        - 删除指定 Emby 用户

        输入参数:
        - user_id: 用户ID

        返回值:
        - Any: 删除结果
        """
        return await self.client.delete_user(user_id)

