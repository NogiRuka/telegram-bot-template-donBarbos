"""使用 xAI 将元数据简介翻译成中文。"""

import json

import aiohttp

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


async def translate_to_chinese(input_text: str) -> str:
    """调用 xAI Responses API 翻译简介并返回纯文本结果。"""
    text = input_text.strip()
    if not text:
        return ""
    if not settings.XAI_API_KEY:
        raise RuntimeError("XAI_API_KEY 未配置")

    payload = {
        "model": settings.XAI_MODEL,
        "instructions": TRANSLATION_INSTRUCTIONS,
        "input": text,
    }
    headers = {
        "Authorization": f"Bearer {settings.XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=90)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.post(settings.XAI_API_BASE, json=payload) as response:
            raw_body = await response.text()
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError:
                body = {"error": {"message": raw_body.strip()}}
            if response.status >= 400:
                message = body.get("error", {}).get("message") if isinstance(body, dict) else None
                raise RuntimeError(message or f"xAI API 请求失败: HTTP {response.status}")
    # xAI 的 Responses API 在不同版本中可能返回 output_text，或把文本放在
    # output[].content[].text / output[].content[].output_text 中。统一递归提取，
    # 避免接口实际成功但前端拿到空字符串后仍显示原文。
    def find_text(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for key in ("output_text", "text"):
                result = find_text(value.get(key))
                if result:
                    return result
            for key in ("output", "content", "message"):
                result = find_text(value.get(key))
                if result:
                    return result
        elif isinstance(value, list):
            for child in value:
                result = find_text(child)
                if result:
                    return result
        return None

    result = find_text(body)
    if result:
        return result
    raise RuntimeError("xAI API 返回中没有找到翻译文本")
