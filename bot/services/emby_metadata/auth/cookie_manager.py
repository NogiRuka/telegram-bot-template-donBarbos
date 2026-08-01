import tomllib
from pathlib import Path

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "cookies.toml"


class CookieManager:
    """读取各元数据站点的本地 Cookie 配置。"""

    def __init__(self, path: str | Path = _DEFAULT_CONFIG_PATH) -> None:
        config_path = Path(path)
        if not config_path.is_file():
            self.config: dict[str, dict[str, object]] = {}
            return
        with config_path.open("rb") as file:
            self.config = tomllib.load(file)

    def get_cookie(self, site: str) -> str | None:
        """返回已启用站点的 Cookie，未配置或禁用时返回空。"""
        data = self.config.get(site)
        if not data or not data.get("enabled", False):
            return None
        cookie = data.get("cookie")
        return cookie.strip() if isinstance(cookie, str) and cookie.strip() else None
