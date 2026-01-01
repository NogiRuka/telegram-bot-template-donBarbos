"""图片工具模块

功能说明:
- 提供通用图片路径获取等工具函数
- 图片尺寸读取

依赖安装:
- pip install Pillow
"""
from pathlib import Path
from typing import IO

from PIL import Image


def get_image_dimensions(file: IO[bytes]) -> tuple[int, int] | None:
    """获取图片尺寸

    功能说明:
    - 从文件流中读取图片尺寸 (宽, 高)
    - 支持各类图片格式

    输入参数:
    - file: 二进制文件流 (BytesIO 或 打开的文件对象)

    返回值:
    - tuple[int, int] | None: (宽, 高) 或 None (若无法读取)
    """
    try:
        with Image.open(file) as img:
            return img.size
    except Exception:
        return None


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
    # 优先检查 Docker 容器内的绝对路径（如果是 Docker 环境）
    docker_path = Path("/usr/src/app/assets/ui/start.jpg")
    if docker_path.exists():
        return str(docker_path)

    # 本地开发环境相对路径
    local_path = Path("assets/ui/start.jpg")
    if local_path.exists():
        return str(local_path)

    return ""

