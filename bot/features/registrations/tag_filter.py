"""
标签屏蔽功能注册

功能说明:
注册用户标签屏蔽功能到功能管理系统
实现"只改一个地方"的开发目标
"""

from bot.features import register_user_feature
from bot.handlers.user.tag_filter import router as tag_filter_router


def register_tag_filter_feature():
    """注册标签屏蔽功能"""
    
    # 🎯 这是唯一需要手动添加的地方！
    # 注册功能会自动完成以下工作：
    # ✅ 生成配置键常量 (KEY_USER_TAG_FILTER)
    # ✅ 添加到功能映射 (USER_FEATURES_MAPPING)
    # ✅ 创建功能按钮 (标签屏蔽)
    # ✅ 应用权限控制 (@require_user_feature)
    # ✅ 集成到用户面板
    
    register_user_feature(
        name="user.tag_filter",
        label="标签屏蔽",
        description="管理用户屏蔽的标签关键词，过滤相关内容",
        # 注意：这里不需要传 handler，因为我们在 router 中已经定义了
        enabled=True,
        show_in_panel=True,
        button_order=60,  # 排序在基本信息之后
    )


# 注册功能
register_tag_filter_feature()

# 导出路由器供其他模块使用
__all__ = ["tag_filter_router"]