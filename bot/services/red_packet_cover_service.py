from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from bot.utils.datetime import now

if TYPE_CHECKING:
    from aiogram.types import User


class RedPacketCoverService:
    @staticmethod
    def _get_assets_dir() -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        return base_dir / "assets" / "redpacket"

    @staticmethod
    def _ensure_output_dir() -> Path:
        output_dir = RedPacketCoverService._get_assets_dir() / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        assets_dir = RedPacketCoverService._get_assets_dir()
        candidates = [
            assets_dir / "fonts" / "NotoSansSC-Regular.otf",
            assets_dir / "fonts" / "NotoSansSC-Regular.ttf",
        ]
        for path in candidates:
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        return ImageFont.load_default()

    @staticmethod
    def _shorten(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

    @staticmethod
    def _build_sender_name(user: User) -> str:
        if user.full_name:
            return user.full_name
        if user.username:
            return f"@{user.username}"
        return "某人"

    @staticmethod
    def generate_cover_image(
        user: User,
        total_amount: int,
        packet_count: int,
        packet_type: str,
        message_text: str,
    ) -> tuple[BytesIO, Path, int]:
        width = 800
        height = 480
        bg_color = (204, 0, 0)
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        title_font = RedPacketCoverService._load_font(40)
        body_font = RedPacketCoverService._load_font(32)
        small_font = RedPacketCoverService._load_font(24)
        sender_name = RedPacketCoverService._build_sender_name(user)
        type_label = "拼手气红包"
        if packet_type == "fixed":
            type_label = "平均分红包"
        elif packet_type == "exclusive":
            type_label = "专属红包"
        safe_message = RedPacketCoverService._shorten(message_text, 20)
        header = f"{sender_name} 发了一个红包"
        amount_line = f"{total_amount} 精粹 · {packet_count} 份"
        type_line = type_label
        message_line = safe_message
        margin_left = 60
        y = 90
        draw.text((margin_left, y), header, font=title_font, fill=(255, 255, 255))
        y += 90
        draw.text((margin_left, y), message_line, font=body_font, fill=(255, 230, 180))
        y += 90
        draw.text((margin_left, y), amount_line, font=body_font, fill=(255, 255, 255))
        y += 60
        draw.text((margin_left, y), type_line, font=small_font, fill=(255, 230, 180))
        footer = now().strftime("%Y-%m-%d %H:%M")
        bbox = draw.textbbox((0, 0), footer, font=small_font)
        footer_w = bbox[2] - bbox[0]
        draw.text((width - footer_w - 40, height - 60), footer, font=small_font, fill=(255, 220, 200))
        output_dir = RedPacketCoverService._ensure_output_dir()
        filename = f"rp_{user.id}_{now().strftime('%Y%m%d%H%M%S%f')}.jpg"
        output_path = output_dir / filename
        img.save(output_path, format="JPEG", quality=90)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        cover_template_id = 1
        return buf, output_path, cover_template_id
