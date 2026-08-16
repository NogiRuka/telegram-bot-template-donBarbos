"""使用 xAI Responses API 将元数据简介翻译成中文。"""

from __future__ import annotations
import asyncio
import json
from collections.abc import Mapping
from typing import Any

import aiohttp
from loguru import logger

from bot.core.config import settings

TRANSLATION_INSTRUCTIONS = """你是一个专业的多语言到中文翻译器。请先自动识别用户输入的语言，再把原文翻译成自然、准确的中文；输入通常是日语，也可能是英语或其他语言。

要求：
- 忠实原意，但不要生硬直译。
- 使用自然、流畅、符合中文习惯的表达。
- 根据上下文准确处理语气、敬语、俚语、口语和习惯表达。
- 如果原文中出现中文读者可能不熟悉的日语词汇、俚语、惯用语、特殊表达或文化用语，保留原文，并在后面用中文括号简短解释其含义。
- 对已经广为人知、无需解释的日语词汇，不需要额外解释；其他语言中的专有名词、俚语或文化表达也按同样原则处理。
- 解释应该简洁，只解释该词在当前上下文中的实际含义，不要展开长篇说明。
- 不要添加原文没有的信息。
- 不要解释翻译过程。
- 不要添加任何标题、前缀或标签。
- 不要输出“译文：”“翻译：”“中文：”等任何开场文字。
- 不要使用 Markdown 标题、代码块或其他格式包裹译文。
- 第一字符必须直接是翻译后的正文。
- 最终只输出翻译内容，不要输出任何其他文字。
- 无论原文是什么语言，都必须输出中文译文；不要原样复述原文。
- 如果原文已经是中文，也只需保持其中文内容，不要添加说明。"""

_MAX_RETRIES = 3
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_RETRY_BACKOFF_SECONDS = 1
_TRANSLATION_CONCURRENCY = 5
_HTTP_ERROR_STATUS = 400


class _TranslationRuntime:
    """保存翻译服务的进程内共享资源。"""

    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.session_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(_TRANSLATION_CONCURRENCY)


_runtime = _TranslationRuntime()


def _build_headers() -> dict[str, str]:
    """返回 xAI 请求所需的认证请求头。"""
    if not settings.XAI_API_KEY:
        msg = "XAI_API_KEY 未配置"
        raise RuntimeError(msg)
    return {
        "Authorization": f"Bearer {settings.XAI_API_KEY}",
        "Content-Type": "application/json",
    }


async def init_translation_session() -> None:
    """初始化应用共享的 xAI HTTP 会话。"""
    if not settings.XAI_API_KEY:
        return
    if _runtime.session is not None and not _runtime.session.closed:
        return

    async with _runtime.session_lock:
        if _runtime.session is None or _runtime.session.closed:
            _runtime.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=90),
                headers=_build_headers(),
            )


async def close_translation_session() -> None:
    """关闭应用共享的 xAI HTTP 会话。"""
    async with _runtime.session_lock:
        if _runtime.session is not None and not _runtime.session.closed:
            await _runtime.session.close()
        _runtime.session = None


async def _get_session() -> aiohttp.ClientSession:
    """返回已初始化的共享 xAI HTTP 会话。"""
    await init_translation_session()
    if _runtime.session is None:
        msg = "xAI HTTP 会话初始化失败"
        raise RuntimeError(msg)
    return _runtime.session


def extract_output_text(body: Mapping[str, Any]) -> str | None:
    """按 Responses API 的 output/message/content/output_text 路径提取译文。"""
    output = body.get("output")
    if not isinstance(output, list):
        return None

    for message in output:
        if not isinstance(message, Mapping) or message.get("type") != "message":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for output_text in content:
            if not isinstance(output_text, Mapping) or output_text.get("type") != "output_text":
                continue
            text = output_text.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def _request_payload(text: str) -> dict[str, Any]:
    """构建单次 xAI Responses API 翻译请求。"""
    payload: dict[str, Any] = {
        "model": settings.XAI_MODEL,
        "store": False,
        "instructions": TRANSLATION_INSTRUCTIONS,
        "input": text,
    }
    if "non-reasoning" not in settings.XAI_MODEL.casefold():
        payload["reasoning"] = {"effort": "low"}
    return payload


async def _post_translation(text: str) -> dict[str, Any]:
    """发送翻译请求，并对暂时性失败执行指数退避重试。"""
    session = await _get_session()
    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with session.post(settings.XAI_API_BASE, json=_request_payload(text)) as response:
                raw_body = await response.text()
                if response.status in _RETRYABLE_STATUSES and attempt < _MAX_RETRIES:
                    logger.warning(
                        "xAI 翻译请求返回 HTTP {}，将重试（{}/{}）",
                        response.status,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                else:
                    try:
                        body = json.loads(raw_body)
                    except json.JSONDecodeError as error:
                        msg = f"xAI API 返回无效 JSON: {raw_body[:500]}"
                        raise RuntimeError(msg) from error

                    if not isinstance(body, dict):
                        msg = "xAI API 返回 JSON 结构无效"
                        raise RuntimeError(msg)
                    if response.status < _HTTP_ERROR_STATUS:
                        return body

                    error = body.get("error")
                    message = error.get("message") if isinstance(error, dict) else None
                    error_message = message if isinstance(message, str) else f"xAI API 请求失败: HTTP {response.status}"
                    raise RuntimeError(error_message)
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            if attempt == _MAX_RETRIES:
                msg = "xAI 翻译服务暂时不可用"
                raise RuntimeError(msg) from error
            logger.warning("xAI 翻译请求失败：{}；将重试（{}/{}）", error, attempt + 1, _MAX_RETRIES)

        await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (2**attempt))

    msg = "xAI 翻译请求重试耗尽"
    raise RuntimeError(msg)


async def translate_to_chinese(input_text: str) -> str:
    """调用 xAI Responses API 翻译简介并返回纯文本结果。"""
    text = input_text.strip()
    if not text:
        return ""
    if not settings.XAI_API_KEY:
        msg = "XAI_API_KEY 未配置"
        raise RuntimeError(msg)

    async with _runtime.semaphore:
        body = await _post_translation(text)
    result = extract_output_text(body)
    if result:
        return result
    msg = "xAI API 返回中没有找到翻译文本"
    raise RuntimeError(msg)
