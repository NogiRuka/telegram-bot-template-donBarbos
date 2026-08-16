现有项目使用 `aiohttp + xAI Responses API` 做多语言转中文翻译，不需要改成 OpenAI SDK。

需要在现有代码基础上优化：

1. 保留现有 `translate_to_chinese()` 调用方式，尽量不要影响其他业务代码。
2. 精简现有翻译 Prompt，但保持以下要求：
   - 自动识别语言并翻译成自然中文。
   - 准确处理日语敬语、俚语、口语和文化表达。
   - 必要时保留特殊原词并用中文括号简短解释。
   - 不添加原文没有的信息。
   - 只输出译文，不输出标题、说明或其他内容。
3. 不要每次翻译都创建新的 `aiohttp.ClientSession`，改成整个应用共享并复用 Session，并在程序退出时正确关闭。
4. xAI 请求保持使用 Responses API：
   - `instructions` 放固定翻译 Prompt。
   - `input` 放原文。
   - 设置 `store=False`。
   - 如果当前模型支持，设置 `reasoning={"effort": "low"}`。
5. 删除现在过于宽松的递归 `find_text()`，按照 Responses API 的 `output → message → content → output_text → text` 精确提取最终译文。
6. 增加 `asyncio.Semaphore` 并发限制，初始并发数建议为 5。
7. 对 `429、500、502、503、504` 以及网络超时增加自动重试，最多重试 3 次，使用指数退避。
8. 保留清晰的异常处理和日志。
9. 最终给出修改后的完整 Python 文件，并说明需要在哪个启动/退出位置初始化或关闭共享 Session。
10. 不要过度重构项目，只针对 xAI 翻译模块做最小必要修改。