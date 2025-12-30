from aiogram import Router

from .group_config import router as group_config_router
from .group_message_saver import router as group_message_saver_router
from .message_export import router as message_export_router


def get_group_router() -> Router:
    """
    聚合群相关路由

    功能说明：
    - 汇总群配置、消息保存与导出等路由为一个 Router

    输入参数：
    - 无

    返回值：
    - Router: 群相关聚合路由
    """
    router = Router(name="group")
    router.include_router(group_config_router)
    router.include_router(message_export_router)
    
    # 消息保存器包含通配符处理器，必须放在最后
    router.include_router(group_message_saver_router)
    return router
