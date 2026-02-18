from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from bot.services.redpacket_preview import (
    RedpacketLayout,
    compose_redpacket_with_info,
)

router = APIRouter()


@router.get("/redpacket/preview")
async def preview_redpacket(
    sender_name: str = Query("测试用户", description="红包发送者名称"),
    message: str = Query("恭喜发财，大吉大利", description="红包留言"),
    amount: float = Query(100.0, ge=0, description="红包总金额"),
    count: int = Query(5, ge=1, description="红包份数"),
    cover_name: str | None = Query(None, description="封面文件名(可选，默认随机)"),
    body_name: str | None = Query(None, description="袋身文件名(可选，默认随机)"),
    watermark_text: str | None = Query("WeChat Team", description="左上角文字水印"),
    avatar_image_name: str | None = Query("sakura.png", description="头像图片文件名"),
    title_font_size: int = Query(88, ge=10, le=200, description="标题字体大小"),
    message_font_size: int = Query(96, ge=10, le=200, description="留言字体大小"),
    amount_font_size: int = Query(110, ge=10, le=240, description="金额字体大小"),
    watermark_font_size: int = Query(52, ge=10, le=200, description="水印字体大小"),
    avatar_size: int = Query(200, ge=40, le=400, description="头像尺寸(像素)"),
    amount_from_bottom: int = Query(260, ge=80, le=400, description="金额距底部像素"),
) -> FileResponse:
    layout = RedpacketLayout(
        title_font_size=title_font_size,
        message_font_size=message_font_size,
        amount_font_size=amount_font_size,
        watermark_font_size=watermark_font_size,
        avatar_size=avatar_size,
        amount_from_bottom=amount_from_bottom,
    )

    path = compose_redpacket_with_info(
        cover_name=cover_name,
        body_name=body_name,
        sender_name=sender_name,
        message=message,
        amount=amount,
        count=count,
        watermark_text=watermark_text,
        watermark_image_name=None,
        avatar_image_name=avatar_image_name,
        layout=layout,
    )

    return FileResponse(path, media_type="image/png")

