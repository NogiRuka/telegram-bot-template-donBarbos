"""OpenAI 本地 token 用量与成本估算。"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bot.core.config import DIR

_DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "cached_input": 0.50, "output": 8.00},
}


class OpenAIUsageTracker:
    """将 OpenAI 响应中的 usage 持久化并生成本地估算。"""

    def __init__(self, log_path: Path | None = None, pricing: dict[str, dict[str, float]] | None = None) -> None:
        """初始化 tracker。价格单位为美元/一百万 token。"""
        self.log_path = log_path or DIR / "data" / "openai_usage.jsonl"
        self.pricing = pricing or _DEFAULT_PRICING

    def _get_pricing(self, model: str) -> dict[str, float] | None:
        if model in self.pricing:
            return self.pricing[model]
        return next((value for key, value in self.pricing.items() if model.startswith(key)), None)

    def estimate_cost(self, model: str, usage: dict[str, Any]) -> float | None:
        """根据 token usage 估算单次请求成本。"""
        price = self._get_pricing(model)
        if price is None:
            return None
        input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
        output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
        details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
        cached_tokens = int(details.get("cached_tokens", 0) or 0) if isinstance(details, dict) else 0
        regular_input_tokens = max(input_tokens - cached_tokens, 0)
        return (
            regular_input_tokens * price["input"]
            + cached_tokens * price.get("cached_input", price["input"])
            + output_tokens * price["output"]
        ) / 1_000_000

    async def record(self, endpoint: str, response: dict[str, Any]) -> None:
        """记录一个包含 usage 的 OpenAI 响应。"""
        usage = response.get("usage")
        model = response.get("model")
        if not isinstance(usage, dict) or not isinstance(model, str):
            return
        details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
        cached_tokens = details.get("cached_tokens", 0) if isinstance(details, dict) else 0
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "model": model,
            "input_tokens": int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0),
            "output_tokens": int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0),
            "cached_tokens": int(cached_tokens or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }
        record["estimated_cost_usd"] = self.estimate_cost(model, usage)
        await asyncio.to_thread(self._append_record, record)

    def _append_record(self, record: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def summary(self, start_time: datetime | None = None) -> dict[str, Any]:
        """汇总本地记录，可按 UTC 起始时间过滤。"""
        records = await asyncio.to_thread(self._read_records)
        if start_time is not None:
            records = [record for record in records if record["timestamp"] >= start_time.isoformat()]
        by_model: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "estimated_cost_usd": 0.0}
        )
        for record in records:
            model_summary = by_model[record["model"]]
            model_summary["requests"] += 1
            for field in ("input_tokens", "output_tokens", "cached_tokens"):
                model_summary[field] += record[field]
            if record["estimated_cost_usd"] is not None:
                model_summary["estimated_cost_usd"] += record["estimated_cost_usd"]
        return {
            "source": "local_response_usage",
            "requests": len(records),
            "input_tokens": sum(record["input_tokens"] for record in records),
            "output_tokens": sum(record["output_tokens"] for record in records),
            "cached_tokens": sum(record["cached_tokens"] for record in records),
            "estimated_cost_usd": sum(record["estimated_cost_usd"] or 0 for record in records),
            "by_model": dict(by_model),
        }

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.log_path.open(encoding="utf-8") as file:
            for line in file:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    records.append(record)
        return records


usage_tracker = OpenAIUsageTracker()
