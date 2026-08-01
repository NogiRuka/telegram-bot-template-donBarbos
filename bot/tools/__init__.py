"""开发辅助工具包。"""

__all__ = ["generate_feature", "sync_users_from_template"]


def __getattr__(name: str):
    """只在访问具体工具时加载对应模块。"""
    if name == "generate_feature":
        from .generate_feature import main

        return main
    if name == "sync_users_from_template":
        from .emby_template_sync import sync_users_from_template

        return sync_users_from_template
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
