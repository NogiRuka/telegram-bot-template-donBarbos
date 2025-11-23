# ruff: noqa: S301
import pickle
from abc import ABC, abstractmethod
from typing import Any

import orjson


class AbstractSerializer(ABC):
    def serialize(self, obj: Any) -> Any:  # pragma: no cover
        """序列化对象为可存储到缓存的字节

        功能说明:
        - 将任意 Python 对象序列化为 `bytes` 或字符串，便于缓存系统存储

        输入参数:
        - obj: 任意 Python 对象

        返回值:
        - Any: 通常为 `bytes` 或 `str`
        """
        raise NotImplementedError

    def deserialize(self, obj: Any) -> Any:  # pragma: no cover
        """反序列化缓存中的字节到 Python 对象

        功能说明:
        - 将缓存中取出的 `bytes` 或字符串还原为 Python 对象

        输入参数:
        - obj: 从缓存读取的原始数据，通常为 `bytes` 或 `str`

        返回值:
        - Any: 还原后的 Python 对象
        """
        raise NotImplementedError


class PickleSerializer(AbstractSerializer):
    """使用 `pickle` 进行序列化/反序列化

    依赖安装:
    - 标准库内置，无需额外安装

    注意事项:
    - `pickle` 反序列化存在安全风险，仅对可信数据源使用
    """

    def serialize(self, obj: Any) -> bytes:
        """序列化为 `bytes`

        输入参数:
        - obj: 任意 Python 对象

        返回值:
        - bytes: 序列化后的字节
        """
        try:
            return pickle.dumps(obj)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"pickle 序列化失败: {exc}") from exc

    def deserialize(self, obj: bytes) -> Any:
        """反序列化 `bytes` 为对象

        输入参数:
        - obj: 缓存中读取的字节

        返回值:
        - Any: 还原后的对象
        """
        try:
            return pickle.loads(obj)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"pickle 反序列化失败: {exc}") from exc


class JSONSerializer(AbstractSerializer):
    """使用 `orjson` 进行 JSON 序列化/反序列化

    依赖安装:
    - pip install orjson
    """

    def serialize(self, obj: Any) -> bytes:
        """序列化为 JSON `bytes`

        输入参数:
        - obj: 可被 JSON 序列化的对象

        返回值:
        - bytes: JSON 字节
        """
        try:
            return orjson.dumps(obj)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"JSON 序列化失败: {exc}") from exc

    def deserialize(self, obj: bytes | str) -> Any:
        """反序列化 JSON 为对象

        输入参数:
        - obj: JSON 字节或字符串

        返回值:
        - Any: 还原后的 Python 对象
        """
        try:
            return orjson.loads(obj)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"JSON 反序列化失败: {exc}") from exc
