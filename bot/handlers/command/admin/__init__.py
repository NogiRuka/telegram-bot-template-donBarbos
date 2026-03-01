import importlib
import pkgutil
from aiogram import Router
from types import ModuleType

def get_admin_command_router() -> Router:
    """
    动态加载 bot.handlers.command.admin 包下所有模块的 router
    """
    router = Router(name="admin_command")
    package_name = __name__
    
    # 遍历当前包下的所有模块
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        try:
            # 动态导入模块
            full_module_name = f"{package_name}.{module_name}"
            module = importlib.import_module(full_module_name)
            
            # 尝试获取模块中的 router 对象
            if hasattr(module, "router") and isinstance(module.router, Router):
                router.include_router(module.router)
        except Exception as e:
            # 记录错误但不中断加载其他模块
            # 这里简单打印或忽略，实际项目中可以使用 logger
            print(f"Failed to load admin command module {module_name}: {e}")
            pass
            
    return router
