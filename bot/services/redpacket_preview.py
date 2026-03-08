from __future__ import annotations
import io
import uuid
import os
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


GROUP_WATERMARK_TEXT = "@lustfulboy_group"

# ========= 全局缓存 =========
BASE_IMAGE_CACHE = {}
FONT_CACHE = {}
MASK_CACHE = {}
WATERMARK_CACHE = {}

def _get_assets_dir() -> Path:
    current_dir = Path(__file__).resolve().parent  # bot/services
    bot_root = current_dir.parent  # bot
    project_root = bot_root.parent

    candidates = [
        bot_root / "assets" / "redpacket",
        project_root / "assets" / "redpacket",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _ensure_output_dir() -> Path:
    env_dir = os.getenv("REDPACKET_PREVIEW_DIR")
    if env_dir:
        out_dir = Path(env_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    try:
        out_dir = _get_assets_dir() / "preview"
        out_dir.mkdir(parents=True, exist_ok=True)
        test_file = out_dir / ".write_test"
        with test_file.open("wb") as f:
            f.write(b"ok")
        try:
            test_file.unlink()
        except FileNotFoundError:
            pass
        return out_dir
    except Exception:
        out_dir = Path(tempfile.gettempdir()) / "redpacket_preview"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir


def _open_image(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def _get_root_assets_dir() -> Path:
    current_dir = Path(__file__).resolve().parent
    bot_root = current_dir.parent
    project_root = bot_root.parent

    candidates = [
        bot_root / "assets",
        project_root / "assets",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _load_fixed_font(rel_path: str, size: int) -> ImageFont.FreeTypeFont:
    assets_root = _get_root_assets_dir()
    font_path = assets_root / rel_path
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size=size)
    return _load_font(size, None)


def _load_avatar_image(avatar_image_name: str | None, size: int) -> Image.Image | None:
    assets_root = _get_root_assets_dir()
    if avatar_image_name:
        av_path = assets_root / "redpacket" / "avatar" / avatar_image_name
    else:
        av_path = assets_root / "redpacket" / "avatar" / "lustfulboy.png"
    if not av_path.exists():
        return None
    av_img = Image.open(av_path).convert("RGBA")
    av_img = av_img.resize((size, size), Image.Resampling.LANCZOS)
    mask_path = assets_root / "redpacket" / "mask" / "avatar.png"
    if mask_path.exists():
        mask_img = Image.open(mask_path).convert("L")
        mask_img = mask_img.resize((size, size), Image.Resampling.LANCZOS)
        av_img.putalpha(mask_img)
    return av_img


def get_font_cached(path: Path | str, size: int) -> ImageFont.FreeTypeFont:
    """获取缓存的字体对象"""
    key = (str(path), size)
    if key not in FONT_CACHE:
        try:
            FONT_CACHE[key] = ImageFont.truetype(str(path), size)
        except Exception:
            # Fallback to default if font fails to load
            FONT_CACHE[key] = ImageFont.load_default()
    return FONT_CACHE[key]


def get_avatar_mask(size: int) -> Image.Image | None:
    """获取缓存的头像遮罩"""
    key = size
    if key in MASK_CACHE:
        return MASK_CACHE[key]

    assets_root = _get_root_assets_dir()
    mask_path = assets_root / "redpacket" / "mask" / "avatar.png"
    if not mask_path.exists():
        return None

    try:
        mask = Image.open(mask_path).convert("L")
        mask = mask.resize((size, size), Image.Resampling.BILINEAR)
        MASK_CACHE[key] = mask
        return mask
    except Exception:
        return None


def get_base_image(cover_name: str, body_name: str) -> Image.Image:
    """获取缓存的底图（封面+主体）"""
    key = f"{cover_name}_{body_name}"
    if key in BASE_IMAGE_CACHE:
        return BASE_IMAGE_CACHE[key].copy()

    assets_dir = _get_assets_dir()
    cover_path = assets_dir / "cover" / cover_name
    body_path = assets_dir / "body" / body_name
    
    # Ensure files exist, otherwise fallback to random or error
    if not cover_path.exists():
        cover_name = _random_asset_file("cover", (".png", ".jpg", ".jpeg"))
        cover_path = assets_dir / "cover" / cover_name
    if not body_path.exists():
        body_name = _random_asset_file("body", (".png", ".jpg", ".jpeg"))
        body_path = assets_dir / "body" / body_name

    cover = _open_image(cover_path)
    body = _open_image(body_path)

    final_width, final_height = 957, 1584
    cover_target_height = 1278
    body_target_height = 480
    body_y = final_height - body_target_height

    scale = final_width / cover.width
    new_height = int(cover.height * scale)
    cover = cover.resize((final_width, new_height), Image.Resampling.BILINEAR)

    if new_height >= cover_target_height:
        cover = cover.crop((0, 0, final_width, cover_target_height))
    else:
        tmp = Image.new("RGBA", (final_width, cover_target_height), (0, 0, 0, 0))
        tmp.paste(cover, (0, 0))
        cover = tmp

    body = body.resize((final_width, body_target_height), Image.Resampling.BILINEAR)

    final_img = Image.new("RGBA", (final_width, final_height), (0, 0, 0, 0))
    final_img.paste(cover, (0, 0))
    final_img.paste(body, (0, body_y), body)

    BASE_IMAGE_CACHE[key] = final_img
    return final_img.copy()


def compose_redpacket(cover_name: str, body_name: str) -> str:
    img = get_base_image(cover_name, body_name)
    
    output_dir = _ensure_output_dir()
    cover_base = cover_name.rsplit(".", 1)[0]
    body_base = body_name.rsplit(".", 1)[0]
    filename = f"rp_{cover_base}__{body_base}.webp"
    output_path = output_dir / filename

    img.save(output_path, format="WEBP", quality=90)
    return str(output_path)


def generate_dynamic_redpacket_preview(name: str, amount: str) -> str:
    return compose_redpacket("C01.jpg", "B01.png")


def get_random_cover_body() -> tuple[str, str]:
    """获取随机的封面和主体文件名"""
    cover = _random_asset_file("cover", (".png", ".jpg", ".jpeg"))
    body = _random_asset_file("body", (".png", ".jpg", ".jpeg"))
    return cover, body


def get_base_image_bytes(cover_name: str, body_name: str) -> tuple[bytes, str]:
    """获取底图的字节流（用于快速发送预览占位）"""
    img = get_base_image(cover_name, body_name)
    import io
    import uuid
    byte_io = io.BytesIO()
    # 占位图不需要太高质量，快速编码即可
    img.save(byte_io, format="WEBP", quality=75, method=0)
    filename = f"preview_{uuid.uuid4().hex}.webp"
    return byte_io.getvalue(), filename


def _load_font(size: int, font_name: str | None = None) -> ImageFont.FreeTypeFont:
    assets_root = _get_root_assets_dir()
    fonts_dir = assets_root / "fonts"
    candidates: list[Path] = []
    if fonts_dir.exists() and fonts_dir.is_dir():
        candidates = [
            p for p in fonts_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".ttf", ".otf", ".ttc")
        ]
    selected: Path | None = None
    if font_name and candidates:
        target = font_name.lower().strip()
        base_target = target.rsplit(".", 1)[0] if target.endswith((".ttf", ".otf", ".ttc")) else target
        for p in candidates:
            name_lower = p.name.lower()
            stem_lower = p.stem.lower()
            if name_lower == target or stem_lower == base_target:
                selected = p
                break
    if not selected:
        system_candidates = [
            Path(r"C:\Windows\Fonts\msyh.ttc"),
            Path(r"C:\Windows\Fonts\msyh.ttf"),
            Path(r"C:\Windows\Fonts\Microsoft YaHei.ttf"),
            Path(r"C:\Windows\Fonts\simhei.ttf"),
            Path(r"C:\Windows\Fonts\simsun.ttc"),
        ]
        available: list[Path] = [p for p in candidates + system_candidates if p.exists()]
        if available:
            selected = random.choice(available)
    if selected:
        return ImageFont.truetype(str(selected), size=size)
    return ImageFont.load_default()


def _random_asset_file(subdir: str, exts: tuple[str, ...]) -> str:
    base = _get_assets_dir() / subdir
    files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in exts]
    if not files:
        msg = f"no asset files in {base}"
        raise FileNotFoundError(msg)
    return random.choice(files).name


@dataclass
class RedpacketLayout:
    title_font_size: int = 60
    message_font_size: int = 96
    amount_font_size: int = 100
    watermark_font_size: int = 30
    avatar_size: int = 210
    amount_from_bottom: int = 80
    title_align: str = "center"
    message_align: str = "center"
    amount_align: str = "center"
    title_dx: int = 0
    title_dy: int = 0
    message_dx: int = 0
    message_dy: int = 0
    amount_dx: int = 0
    amount_dy: int = 0
    watermark_dx: int = 0
    watermark_dy: int = 0
    title_color: tuple[int, int, int] = (235, 205, 154)
    message_color: tuple[int, int, int] = (235, 205, 154)
    amount_color: tuple[int, int, int] = (235, 205, 154)
    watermark_color: tuple[int, int, int] = (235, 205, 154)
    shadow_enabled: bool = True
    shadow_offset_x: int = 2
    shadow_offset_y: int = 2
    shadow_color: tuple[int, int, int] = (0, 0, 0)
    font_name: str | None = None


def _resolve_anchor(horizontal: str, base_anchor: str) -> str:
    if not base_anchor:
        base_anchor = "mm"
    v = base_anchor[1] if len(base_anchor) > 1 else "m"
    h = horizontal.lower()
    if h == "left":
        h_char = "l"
    elif h == "right":
        h_char = "r"
    else:
        h_char = "m"
    return f"{h_char}{v}"


def _draw_text_with_layout(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    base_anchor: str,
    align: str,
    dx: int,
    dy: int,
    layout: RedpacketLayout,
) -> None:
    x = position[0] + dx
    y = position[1] + dy
    anchor = _resolve_anchor(align, base_anchor)
    if layout.shadow_enabled:
        sx = x + layout.shadow_offset_x
        sy = y + layout.shadow_offset_y
        draw.text((sx, sy), text, font=font, fill=layout.shadow_color, anchor=anchor)
    draw.text((x, y), text, font=font, fill=color, anchor=anchor)


def compose_redpacket_with_info(
    cover_name: str | None,
    body_name: str | None,
    sender_name: str,
    amount: float,
    count: int,
    group_text: str | None = GROUP_WATERMARK_TEXT,
    watermark_image_name: str | None = None,
    avatar_image_name: str | None = None,
    layout: RedpacketLayout | None = None,
    avatar_file_content: bytes | None = None,
    return_bytes: bool = False,
) -> str | tuple[bytes, str]:
    if cover_name is None:
        cover_name = _random_asset_file("cover", (".png", ".jpg", ".jpeg"))
    if body_name is None:
        body_name = _random_asset_file("body", (".png", ".jpg", ".jpeg"))

    # 1. 获取缓存底图
    img = get_base_image(cover_name, body_name)
    draw = ImageDraw.Draw(img)
    width, height = img.size
    center_x = width // 2

    assets_root = _get_root_assets_dir()

    # 2. 获取缓存字体
    # 为了性能，优先使用固定字体配置，忽略 layout 中的部分字体配置
    # 如果需要完全自定义，可以在这里扩展，但会牺牲部分缓存命中率
    title_font = get_font_cached(assets_root / "fonts/redpacket/simhei.ttf", 60)
    amount_font = get_font_cached(assets_root / "fonts/redpacket/方正喵呜体.ttf", 100)
    
    # 3. 处理头像
    avatar_size = 210
    avatar_y = 130
    
    av_img = None
    if avatar_file_content:
        try:
            av_img = Image.open(io.BytesIO(avatar_file_content)).convert("RGBA")
            av_img = av_img.resize((avatar_size, avatar_size), Image.Resampling.BILINEAR)
            
            # 获取并应用缓存遮罩
            mask = get_avatar_mask(avatar_size)
            if mask:
                av_img.putalpha(mask)
        except Exception:
            pass
            
    if av_img is None:
        # Fallback to default avatar
        av_img = _load_avatar_image(avatar_image_name, avatar_size)

    # -----------------------------------------------------------
    # [坐标配置区域] 修改下方的坐标值可调整元素位置
    # -----------------------------------------------------------

    # 1. 头像位置
    # 头像大小：100x100 像素
    avatar_size = 100
    # 头像垂直位置 (Y轴)：距离顶部 135 像素
    avatar_y = 135
    
    if av_img:
        av_img = av_img.resize((avatar_size, avatar_size))
        # 粘贴头像：(水平居中, 指定Y坐标)
        img.paste(av_img, (center_x - avatar_size // 2, avatar_y), av_img)

    # 2. 发送者昵称位置
    # 字体大小：60
    # 垂直位置 (Y轴)：头像底部 + 60 像素
    nickname_y = avatar_y + avatar_size + 60
    sender_text = f"{sender_name} 的红包"
    
    draw.text(
        (center_x, nickname_y),
        sender_text,
        font=title_font,
        fill=(235, 205, 154), # 字体颜色 (RGB)
        anchor="mm",          # 锚点：水平垂直居中
    )

    # 3. 红包金额/数量位置
    # 字体大小：100
    # 垂直位置 (Y轴)：距离底部 80 像素
    amount_y = height - 80
    amount_text = f"{amount:.0f}/{count}"
    
    draw.text(
        (center_x, amount_y),
        amount_text,
        font=amount_font,
        fill=(235, 205, 154), # 字体颜色 (RGB)
        anchor="mm",          # 锚点：水平垂直居中
    )
    
    # -----------------------------------------------------------
    # [结束] 坐标配置区域
    # -----------------------------------------------------------

    # 5. 生成结果 (WebP + 内存操作)
    import uuid
    filename = f"rp_{uuid.uuid4().hex}.webp"

    if return_bytes:
        byte_io = io.BytesIO()
        # WebP method=4 平衡速度和大小
        img.save(byte_io, format="WEBP", quality=80, method=4)
        return byte_io.getvalue(), filename

    output_dir = _ensure_output_dir()
    output_path = output_dir / filename
    img.save(output_path, format="WEBP", quality=80, method=4)
    return str(output_path)
