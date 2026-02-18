from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import random

from PIL import Image, ImageDraw, ImageFont


def _get_assets_dir() -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent
    return base_dir / "assets" / "redpacket"


def _ensure_output_dir() -> Path:
    out_dir = _get_assets_dir() / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _open_image(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


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


def _get_root_assets_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "assets"


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    assets_root = _get_root_assets_dir()
    fonts_dir = assets_root / "fonts"
    candidates: list[Path] = []
    if fonts_dir.exists() and fonts_dir.is_dir():
        candidates = [
            p for p in fonts_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".ttf", ".otf", ".ttc")
        ]
    system_candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyh.ttf"),
        Path(r"C:\Windows\Fonts\Microsoft YaHei.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    available: list[Path] = [p for p in candidates + system_candidates if p.exists()]
    if available:
        chosen = random.choice(available)
        return ImageFont.truetype(str(chosen), size=size)
    return ImageFont.load_default()


def _random_asset_file(subdir: str, exts: tuple[str, ...]) -> str:
    base = _get_assets_dir() / subdir
    files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in exts]
    if not files:
        raise FileNotFoundError(f"no asset files in {base}")
    return random.choice(files).name


@dataclass
class RedpacketLayout:
    title_font_size: int = 88
    message_font_size: int = 96
    amount_font_size: int = 110
    watermark_font_size: int = 52
    avatar_size: int = 200
    amount_from_bottom: int = 260


def compose_redpacket_with_info(
    cover_name: str | None,
    body_name: str | None,
    sender_name: str,
    message: str,
    amount: float,
    count: int,
    watermark_text: str | None = None,
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

    title_font = _load_font(layout.title_font_size)
    message_font = _load_font(layout.message_font_size)
    amount_font = _load_font(layout.amount_font_size)
    watermark_font = _load_font(layout.watermark_font_size)

    if watermark_image_name:
        wm_path = _get_root_assets_dir() / watermark_image_name
        if wm_path.exists():
            wm_img = Image.open(wm_path).convert("RGBA")
            max_w = 260
            scale = min(1.0, max_w / wm_img.width)
            new_size = (int(wm_img.width * scale), int(wm_img.height * scale))
            wm_img = wm_img.resize(new_size, Image.Resampling.LANCZOS)
            img.paste(wm_img, (60, 96), wm_img)
    if watermark_text:
        draw.text((60, 96), watermark_text, font=watermark_font, fill=(255, 255, 255))

    avatar_size = layout.avatar_size
    avatar_x = center_x - avatar_size - 32
    avatar_y = 360
    if avatar_image_name:
        av_path = _get_root_assets_dir() / avatar_image_name
        if av_path.exists():
            av_img = Image.open(av_path).convert("RGBA")
            av_img = av_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            img.paste(av_img, (avatar_x, avatar_y), av_img)

    sender_text = f"{sender_name}的红包"
    draw.text(
        (center_x + 60, avatar_y + avatar_size / 2),
        sender_text,
        font=title_font,
        fill=(255, 255, 255),
        anchor="lm",
    )

    draw.text(
        (center_x, avatar_y + avatar_size + 120),
        message,
        font=message_font,
        fill=(255, 255, 255),
        anchor="mm",
    )

    amount_text = f"{amount:.0f} 💧 / {count}"
    draw.text(
        (center_x, height - layout.amount_from_bottom),
        amount_text,
        font=amount_font,
        fill=(255, 255, 255),
        anchor="mm",
    )

    output_dir = _ensure_output_dir()
    cover_base = cover_name.rsplit(".", 1)[0]
    body_base = body_name.rsplit(".", 1)[0]
    filename = f"rp_info_{cover_base}__{body_base}.png"
    output_path = output_dir / filename
    img.convert("RGB").save(output_path, format="PNG")
    return str(output_path)
