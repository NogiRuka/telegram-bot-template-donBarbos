import tomllib


class CookieManager:

    def __init__(self, path="config/cookies.toml"):
        with open(path, "rb") as f:
            self.config = tomllib.load(f)


    def get_cookie(self, site: str):
        data = self.config.get(site)

        if not data:
            return None

        if not data.get("enabled", False):
            return None

        return data.get("cookie")