"""使用 xAI 将元数据简介翻译成中文。"""

import aiohttp

from bot.core.config import settings


TRANSLATION_PROMPT = """将以下内容自然、准确地翻译成中文。

要求：
- 忠实原意，但不要生硬直译。
- 使用自然、流畅、符合中文习惯的表达。
- 根据上下文准确处理语气、敬语、俚语、口语和习惯表达。
- 如果原文中出现中文读者可能不熟悉的日语词汇、俚语、惯用语、特殊表达或文化用语，保留原文，并在后面用中文括号简短解释其含义。
- 对已经广为人知、无需解释的日语词汇，不需要额外解释。
- 解释应该简洁，只解释该词在当前上下文中的实际含义，不要展开长篇说明。
- 不要添加原文没有的信息。
- 不要解释翻译过程。
- 最终只输出中文译文。

原文：
{input_text}"""


async def translate_to_chinese(input_text: str) -> str:
    """调用 xAI Responses API 翻译简介并返回纯文本结果。"""
    text = input_text.strip()
    if not text:
        return ""
    if not settings.XAI_API_KEY:
        raise RuntimeError("XAI_API_KEY 未配置")

    payload = {
        "model": settings.XAI_MODEL,
        "input": TRANSLATION_PROMPT.format(input_text=text),
    }
    headers = {
        "Authorization": f"Bearer {settings.XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=90)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.post(settings.XAI_API_BASE, json=payload) as response:
            body = await response.json(content_type=None)
            if response.status >= 400:
                message = body.get("error", {}).get("message") if isinstance(body, dict) else None
                raise RuntimeError(message or f"xAI API 请求失败: HTTP {response.status}")
    result = body.get("output_text") if isinstance(body, dict) else None
    if isinstance(result, str) and result.strip():
        return result.strip()
    if isinstance(body, dict):
        for output in body.get("output", []):
            for content in output.get("content", []) if isinstance(output, dict) else []:
                text_value = content.get("text") if isinstance(content, dict) else None
                if isinstance(text_value, str) and text_value.strip():
                    return text_value.strip()
    raise RuntimeError("xAI API 返回中没有找到翻译文本")
