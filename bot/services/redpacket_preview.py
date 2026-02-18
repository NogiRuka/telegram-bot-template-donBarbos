from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _get_assets_dir() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "assets" / "redpacket"


def _ensure_output_dir() -> Path:
    out_dir = _get_assets_dir() / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    assets_dir = _get_assets_dir()
    candidates = [
        assets_dir / "fonts" / "NotoSansSC-Regular.otf",
        assets_dir / "fonts" / "NotoSansSC-Regular.ttf",
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def _shorten(text: str, max_len: int) -> str:
    text = text or ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def generate_dynamic_redpacket_preview(name: str, amount: str) -> str:
    width, height = 957, 1278
    total_amount = float(amount)

    title_font = _load_font(64)
    amount_font = _load_font(120)
    tip_font = _load_font(40)

    safe_name = _shorten(name, 10)
    output_dir = _ensure_output_dir()
    filename = f"wx_preview_{safe_name}.png"
    output_path = output_dir / filename

    img = Image.new("RGB", (width, height), (240, 80, 60))
    draw = ImageDraw.Draw(img)

    center_x = width // 2

    # 顶部福章
    draw.ellipse(
        [center_x - 100, 150, center_x + 100, 350],
        fill=(255, 215, 0),
    )
    draw.text(
        (center_x, 250),
        "福",
        font=title_font,
        fill=(200, 0, 0),
        anchor="mm",
    )

    # 名字
    draw.text(
        (center_x, 420),
        f"{safe_name}的红包",
        font=tip_font,
        fill=(255, 230, 180),
        anchor="mm",
    )

    # 金额
    draw.text(
        (center_x, 600),
        f"¥ {total_amount:,.2f}",
        font=amount_font,
        fill=(255, 255, 255),
        anchor="mm",
    )

    img.save(output_path, format="PNG")

    return str(output_path)
