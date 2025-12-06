"""图片工具模块

功能说明:
- 提供通用图片路径获取等工具函数

依赖安装:
- 无额外依赖
"""
from pathlib import Path


def get_common_image() -> str:
    """通用图片选择器

    功能说明:
    - 返回统一使用的主消息图片路径, 不依赖角色
    - 若图片不存在, 返回空字符串, 调用方仅编辑文本

    输入参数:
    - 无

    返回值:
    - str: 图片文件路径; 若不可用则返回空字符串
    """
    target = Path("assets/ui/start.jpg")
    return str(target) if target.exists() else ""

