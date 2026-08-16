import tomllib
from pathlib import Path

_CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
_DEFAULT_CONFIG_DIR = _CONFIG_ROOT / "cookies"
_LEGACY_CONFIG_PATH = _CONFIG_ROOT / "cookies.toml"


class CookieManager:
    """读取各元数据站点的本地 Cookie 配置。"""

    def __init__(self, path: str | Path = _DEFAULT_CONFIG_DIR) -> None:
        config_path = Path(path)
        self.config: dict[str, dict[str, object]] = {}
        self.legacy_config: dict[str, dict[str, object]] = {}

        if config_path.is_dir():
            for cookie_file in config_path.glob("*.toml"):
                with cookie_file.open("rb") as file:
                    self.config[cookie_file.stem] = tomllib.load(file)
            if _LEGACY_CONFIG_PATH.is_file():
                with _LEGACY_CONFIG_PATH.open("rb") as file:
                    self.legacy_config = tomllib.load(file)
        elif config_path.is_file():
            with config_path.open("rb") as file:
                self.legacy_config = tomllib.load(file)

    def get_cookie(self, site: str) -> str | None:
        """返回指定数据源的 Cookie，未配置或禁用时返回空。"""
        data = self.config.get(site) or self.legacy_config.get(site)
        if not data or not data.get("enabled", False):
            return None
        cookie = data.get("cookie")
        return cookie.strip() if isinstance(cookie, str) and cookie.strip() else None
