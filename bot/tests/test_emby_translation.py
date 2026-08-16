"""xAI 翻译模块的单元测试。"""

from __future__ import annotations
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from bot.services.emby_metadata import translation


class TranslationTests(unittest.TestCase):
    """验证 Responses API 译文提取和调用边界。"""

    def tearDown(self) -> None:
        asyncio.run(translation.close_translation_session())

    def test_extract_output_text_uses_response_message_path(self) -> None:
        body = {
            "output": [
                {"type": "reasoning", "content": [{"type": "output_text", "text": "忽略"}]},
                {"type": "message", "content": [{"type": "output_text", "text": "  中文译文  "}]},
            ]
        }
        assert translation.extract_output_text(body) == "中文译文"

    def test_extract_output_text_rejects_unexpected_shapes(self) -> None:
        assert translation.extract_output_text({"output": {"text": "错误路径"}}) is None
        assert translation.extract_output_text({"output": []}) is None

    @patch("bot.services.emby_metadata.translation._post_translation", new_callable=AsyncMock)
    def test_translate_to_chinese_preserves_empty_input(self, post_translation: AsyncMock) -> None:
        assert asyncio.run(translation.translate_to_chinese("  \n")) == ""
        post_translation.assert_not_awaited()

    @patch("bot.services.emby_metadata.translation._post_translation", new_callable=AsyncMock)
    def test_translate_to_chinese_returns_response_text(self, post_translation: AsyncMock) -> None:
        post_translation.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "译文"}]}]
        }
        assert asyncio.run(translation.translate_to_chinese("original")) == "译文"
        post_translation.assert_awaited_once_with("original")


if __name__ == "__main__":
    unittest.main()
