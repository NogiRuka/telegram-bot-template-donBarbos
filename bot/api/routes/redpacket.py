from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from bot.services.redpacket_preview import (
    GROUP_WATERMARK_TEXT,
    RedpacketLayout,
    compose_redpacket_with_info,
)


def _parse_color(value: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if not value:
        return default
    s = value.strip()
    s = s.removeprefix("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return default
    try:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
    except ValueError:
        return default
    return (r, g, b)


router = APIRouter()


@router.get("/redpacket/preview")
async def preview_redpacket(
    sender_name: Annotated[str, Query(description="红包发送者名称")] = "测试用户",
    amount: Annotated[float, Query(ge=0, description="红包总金额")] = 100.0,
    count: Annotated[int, Query(ge=1, description="红包份数")] = 5,
    cover_name: Annotated[str | None, Query(description="封面文件名(可选，默认随机)")] = None,
    body_name: Annotated[str | None, Query(description="袋身文件名(可选，默认随机)")] = None,
    group_text: Annotated[str | None, Query(description="右下角群组文字水印")] = GROUP_WATERMARK_TEXT,
    avatar_image_name: Annotated[str | None, Query(description="头像图片文件名")] = None,
    title_font_size: Annotated[int, Query(ge=10, le=200, description="标题字体大小")] = 88,
    message_font_size: Annotated[int, Query(ge=10, le=200, description="留言字体大小")] = 96,
    amount_font_size: Annotated[int, Query(ge=10, le=240, description="金额字体大小")] = 110,
    watermark_font_size: Annotated[int, Query(ge=10, le=200, description="水印字体大小")] = 52,
    avatar_size: Annotated[int, Query(ge=40, le=400, description="头像尺寸(像素)")] = 200,
    amount_from_bottom: Annotated[int, Query(ge=80, le=400, description="金额距底部像素")] = 260,
    title_align: Annotated[str, Query(description="标题水平对齐方式")] = "left",
    message_align: Annotated[str, Query(description="留言水平对齐方式")] = "center",
    amount_align: Annotated[str, Query(description="金额水平对齐方式")] = "center",
    title_dx: Annotated[int, Query(description="标题X偏移")] = 0,
    title_dy: Annotated[int, Query(description="标题Y偏移")] = 0,
    message_dx: Annotated[int, Query(description="留言X偏移")] = 0,
    message_dy: Annotated[int, Query(description="留言Y偏移")] = 0,
    amount_dx: Annotated[int, Query(description="金额X偏移")] = 0,
    amount_dy: Annotated[int, Query(description="金额Y偏移")] = 0,
    watermark_dx: Annotated[int, Query(description="水印X偏移")] = 0,
    watermark_dy: Annotated[int, Query(description="水印Y偏移")] = 0,
    title_color: Annotated[str, Query(description="标题颜色")] = "ffffff",
    message_color: Annotated[str, Query(description="留言颜色")] = "ffffff",
    amount_color: Annotated[str, Query(description="金额颜色")] = "ffffff",
    watermark_color: Annotated[str, Query(description="水印颜色")] = "ffffff",
    shadow_enabled: Annotated[bool, Query(description="是否启用文字阴影")] = True,
    shadow_offset_x: Annotated[int, Query(description="阴影X偏移")] = 2,
    shadow_offset_y: Annotated[int, Query(description="阴影Y偏移")] = 2,
    shadow_color: Annotated[str, Query(description="阴影颜色")] = "000000",
    font_name: Annotated[str | None, Query(description="字体文件名")] = None,
) -> FileResponse:
    layout = RedpacketLayout(
        title_font_size=title_font_size,
        message_font_size=message_font_size,
        amount_font_size=amount_font_size,
        watermark_font_size=watermark_font_size,
        avatar_size=avatar_size,
        amount_from_bottom=amount_from_bottom,
        title_align=title_align,
        message_align=message_align,
        amount_align=amount_align,
        title_dx=title_dx,
        title_dy=title_dy,
        message_dx=message_dx,
        message_dy=message_dy,
        amount_dx=amount_dx,
        amount_dy=amount_dy,
        watermark_dx=watermark_dx,
        watermark_dy=watermark_dy,
        title_color=_parse_color(title_color, (255, 255, 255)),
        message_color=_parse_color(message_color, (255, 255, 255)),
        amount_color=_parse_color(amount_color, (255, 255, 255)),
        watermark_color=_parse_color(watermark_color, (255, 255, 255)),
        shadow_enabled=shadow_enabled,
        shadow_offset_x=shadow_offset_x,
        shadow_offset_y=shadow_offset_y,
        shadow_color=_parse_color(shadow_color, (0, 0, 0)),
        font_name=font_name,
    )

    path = compose_redpacket_with_info(
        cover_name=cover_name,
        body_name=body_name,
        sender_name=sender_name,
        amount=amount,
        count=count,
        group_text=group_text,
        watermark_image_name=None,
        avatar_image_name=avatar_image_name,
        layout=layout,
    )

    return FileResponse(path, media_type="image/png")
