from __future__ import annotations
import os
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


GROUP_WATERMARK_TEXT = "@lustfulboy_group"


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


def compose_redpacket(cover_name: str, body_name: str) -> str:
    assets_dir = _get_assets_dir()
    cover_path = assets_dir / "cover" / cover_name
    body_path = assets_dir / "body" / body_name

    cover = _open_image(cover_path)
    body = _open_image(body_path)

    final_width, final_height = 957, 1584
    cover_target_height = 1278
    body_target_height = 480
    body_y = final_height - body_target_height

    scale = final_width / cover.width
    new_height = int(cover.height * scale)
    cover = cover.resize((final_width, new_height), Image.Resampling.LANCZOS)

    if new_height >= cover_target_height:
        cover = cover.crop((0, 0, final_width, cover_target_height))
    else:
        tmp = Image.new("RGBA", (final_width, cover_target_height), (0, 0, 0, 0))
        tmp.paste(cover, (0, 0))
        cover = tmp

    body = body.resize((final_width, body_target_height), Image.Resampling.LANCZOS)

    final_img = Image.new("RGBA", (final_width, final_height), (0, 0, 0, 0))
    final_img.paste(cover, (0, 0))
    final_img.paste(body, (0, body_y), body)

    output_dir = _ensure_output_dir()
    cover_base = cover_name.rsplit(".", 1)[0]
    body_base = body_name.rsplit(".", 1)[0]
    filename = f"rp_{cover_base}__{body_base}.png"
    output_path = output_dir / filename

    final_img = final_img.convert("RGB")
    final_img.save(output_path, format="PNG")
    return str(output_path)


def generate_dynamic_redpacket_preview(name: str, amount: str) -> str:
    return compose_redpacket("C01.jpg", "B01.png")


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
) -> str:
    if cover_name is None:
        cover_name = _random_asset_file("cover", (".png", ".jpg", ".jpeg"))
    if body_name is None:
        body_name = _random_asset_file("body", (".png", ".jpg", ".jpeg"))

    base_path = compose_redpacket(cover_name, body_name)
    img = Image.open(base_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    width, height = img.size
    center_x = width // 2

    layout = layout or RedpacketLayout()

    if watermark_image_name is None:
        watermark_image_name = "redpacket/watermark/lustfulboy.png"

    if layout.font_name:
        title_font = _load_font(layout.title_font_size, layout.font_name)
        message_font = _load_font(layout.message_font_size, layout.font_name)
        amount_font = _load_font(layout.amount_font_size, layout.font_name)
        watermark_font = _load_font(layout.watermark_font_size, layout.font_name)
        group_font = watermark_font
    else:
        title_font = _load_fixed_font("fonts/redpacket/simhei.ttf", layout.title_font_size)
        message_font = _load_fixed_font("fonts/redpacket/simhei.ttf", layout.message_font_size)
        amount_font = _load_fixed_font("fonts/redpacket/方正喵呜体.ttf", layout.amount_font_size)
        watermark_font = _load_fixed_font("fonts/redpacket/segoepr.ttf", layout.watermark_font_size)
        group_font = _load_fixed_font("fonts/redpacket/segoepr.ttf", layout.watermark_font_size)

    if watermark_image_name:
        wm_path = _get_root_assets_dir() / watermark_image_name
        if wm_path.exists():
            wm_img = Image.open(wm_path).convert("RGBA")
            size = 80
            wm_img = wm_img.resize((size, size), Image.Resampling.LANCZOS)
            img.paste(wm_img, (11, 11), wm_img)

    avatar_size = layout.avatar_size
    avatar_y = 130
    avatar_x = center_x - avatar_size // 2
    av_img = _load_avatar_image(avatar_image_name, avatar_size)
    if av_img is not None:
        img.paste(av_img, (avatar_x, avatar_y), av_img)

    sender_text = f"{sender_name}的红包"
    sender_pos = (float(center_x), float(avatar_y + avatar_size + 60))
    _draw_text_with_layout(
        draw,
        sender_pos,
        sender_text,
        title_font,
        layout.title_color,
        "mm",
        layout.title_align,
        layout.title_dx,
        layout.title_dy,
        layout,
    )

    amount_text = f"{amount:.0f}/{count}"
    amount_pos = (float(center_x), float(height - layout.amount_from_bottom))
    original_shadow = layout.shadow_enabled
    layout.shadow_enabled = False
    _draw_text_with_layout(
        draw,
        amount_pos,
        amount_text,
        amount_font,
        layout.amount_color,
        "mm",
        layout.amount_align,
        layout.amount_dx,
        layout.amount_dy,
        layout,
    )
    layout.shadow_enabled = original_shadow

    if not group_text:
        group_text = GROUP_WATERMARK_TEXT
    margin_x = 10.0
    margin_y = 10.0
    group_pos = (float(width) - margin_x, float(height) - margin_y)
    anchor = "rb"
    draw.text(group_pos, group_text, font=group_font, fill=layout.watermark_color, anchor=anchor)

    output_dir = _ensure_output_dir()
    cover_base = cover_name.rsplit(".", 1)[0]
    body_base = body_name.rsplit(".", 1)[0]
    filename = f"rp_info_{cover_base}__{body_base}.png"
    output_path = output_dir / filename
    img.convert("RGB").save(output_path, format="PNG")
    return str(output_path)
