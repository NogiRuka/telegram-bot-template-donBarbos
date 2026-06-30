from __future__ import annotations

from typing import Any


def _to_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def render_usage_lines(meta: dict[str, Any]) -> list[str]:
    usage = meta.get("usage")
    example = meta.get("example")

    if isinstance(usage, dict):
        lines: list[str] = []
        summary = _to_str_list(usage.get("summary"))
        formats = _to_str_list(usage.get("formats"))
        examples = _to_str_list(usage.get("examples"))
        if summary:
            lines.extend([f"    {line}" for line in summary])
        if formats:
            if lines:
                lines.append("    格式:")
            for idx, line in enumerate(formats, start=1):
                lines.append(f"    {idx}. {line}")
        if examples:
            if lines:
                lines.append("    示例:")
            for idx, line in enumerate(examples, start=1):
                lines.append(f"    {idx}. {line}")
        return lines

    lines = [f"    {line}" for line in _to_str_list(usage)]
    if isinstance(example, dict):
        example_command = str(example.get("command") or "").strip()
        example_explain = str(example.get("explain") or "").strip()
        if example_command:
            if lines:
                lines.append("    示例:")
            lines.append(f"    {example_command}")
            if example_explain:
                lines.append(f"    {example_explain}")
    return lines


def build_usage_text(meta: dict[str, Any]) -> str:
    lines = ["用法:"]
    usage = meta.get("usage")
    if isinstance(usage, dict):
        summary = _to_str_list(usage.get("summary"))
        formats = _to_str_list(usage.get("formats"))
        examples = _to_str_list(usage.get("examples"))

        if summary:
            lines.extend([f"`{line}`" for line in summary])
        if formats:
            lines.extend(["", "格式:"])
            lines.extend([f"{idx}. `{line}`" for idx, line in enumerate(formats, start=1)])
        if examples:
            lines.extend(["", "示例:"])
            lines.extend([f"{idx}. `{line}`" for idx, line in enumerate(examples, start=1)])
    else:
        usage_lines = _to_str_list(usage)
        if usage_lines:
            lines.extend([f"`{line}`" for line in usage_lines])

    example = meta.get("example")
    if isinstance(example, dict):
        example_command = str(example.get("command") or "").strip()
        example_explain = str(example.get("explain") or "").strip()
        if example_command:
            lines.extend(["", "示例:", f"`{example_command}`"])
            if example_explain:
                lines.append(example_explain)

    return "\n".join(lines)
