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
from loguru import logger


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
    # 动态获取项目根目录（基于当前文件位置）
    # 当前文件在 bot/utils/images.py，根目录需向上回退 3 层
    base_dir = Path(__file__).resolve().parent.parent.parent
    logger.info(f"当前项目根目录: {base_dir}")

    # 优先检查 Docker 容器内的路径（如果当前是在容器内运行，通常是 /usr/src/app）
    # 但由于 base_dir 已经是动态计算的，只要文件确实存在于容器内的对应位置，pathlib 就能找到
    # 关键在于 assets 目录是否被正确 COPY 或 VOLUME 挂载进去了
    
    # 尝试多个可能的路径（兼容 Docker 和本地开发）
    candidates = [
        base_dir / "assets/ui/start.jpg",
        Path("/usr/src/app/assets/ui/start.jpg"),  # Docker 绝对路径
        Path("/app/assets/ui/start.jpg"),          # 常见 Docker 路径
        Path("assets/ui/start.jpg").resolve(),     # 相对路径
    ]

    for target in candidates:
        if target.exists():
            logger.info(f"找到图片: {target}")
            return str(target)
    
    logger.warning(f"未找到默认图片，搜索路径: {[str(p) for p in candidates]}")
    return ""

