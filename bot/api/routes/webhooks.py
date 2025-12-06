"""
Webhooks 路由
处理来自 Emby 的 Webhook 回调请求
"""

from __future__ import annotations
import json
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request

try:
    import orjson
except Exception:
    orjson = None  # type: ignore
from loguru import logger

router = APIRouter()


@router.post("/webhooks/emby")
async def handle_emby_webhook(
    request: Request,
    x_emby_event: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """
    处理 Emby Webhook 回调

    功能说明:
    - 接收 Emby Webhooks 插件发送的事件回调 (POST JSON)
    - 尽量兼容不同事件载荷结构, 进行日志记录与基本回执

    输入参数:
    - request: FastAPI 的请求对象, 用于读取原始 JSON 载荷
    - x_emby_event: 请求头 `X-Emby-Event` (可选), 某些配置会附带事件名

    返回值:
    - dict: 处理结果, 包含状态与解析的关键信息
    """

    # 读取 JSON 载荷
    try:
        payload: dict[str, Any] = await request.json()
    except (ValueError, UnicodeDecodeError) as err:
        logger.exception("❌ 解析 Emby Webhook JSON 失败")
        raise HTTPException(status_code=400, detail="Invalid JSON body") from err

    pretty = format_json_pretty(payload)
    logger.info("📥 收到 Emby Webhook 原始载荷:\n{}", pretty)

    # 这里可以根据不同事件进行业务处理, 例如:
    # - PlaybackStart / PlaybackStop: 统计观看记录
    # - ItemAdded: 同步媒资到数据库
    # - UserDeleted: 清理相关数据
    # 为了安全示范, 本模板仅做日志记录与回执; 可根据需求接入 bot.services 中的业务逻辑

    # 简单回执，仅返回收到的 event 头与解析到的 payload
    return {
        "status": "ok",
        "x_emby_event": x_emby_event,
        "payload": payload,
    }


def format_json_pretty(data: Any) -> str:
    """将对象美化为 JSON 字符串

    功能说明：
    - 优先使用 `orjson` 进行缩进美化并保持非 ASCII 字符
    - 兼容回退到标准库 `json.dumps`，`ensure_ascii=False` 防止中文被转义

    输入参数：
    - data: 任意可序列化对象（通常为 dict / list）

    返回值：
    - str: 缩进美化后的 JSON 字符串

    依赖安装方式：
    - `pip install orjson`（已在项目依赖中声明）
    """
    try:
        if orjson is not None:
            return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        try:
            return json.dumps({"unserializable": str(type(data))}, ensure_ascii=False)
        except Exception:
            return "{}"
