class MetadataSourceError(Exception):
    """元数据数据源错误基类。"""

    def __init__(self, message: str, source: str) -> None:
        super().__init__(f"{source}: {message}")
        self.message = message
        self.source = source


class MetadataSourceNetworkError(MetadataSourceError):
    """数据源网络请求失败。"""


class MetadataSourceHTTPError(MetadataSourceError):
    """数据源返回 HTTP 错误。"""


class MetadataSourceParseError(MetadataSourceError):
    """数据源页面结构解析失败。"""
