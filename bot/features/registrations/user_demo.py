"""
user.demo功能注册

功能说明:
注册user.demo功能到系统中
"""

from bot.features import register_user_feature
from bot.handlers.user.user_demo import handle_demo


def register_user_demo_feature():
    """注册user.demo功能"""
    register_user_feature(
        name="user.demo",
        label="演示功能",
        description="这是一个演示新功能开发流程的功能",
        handler=handle_demo,
        enabled=True,
        show_in_panel=True,
        button_order=50,  # 调整按钮排序
    )


# 注册功能
register_user_demo_feature()
