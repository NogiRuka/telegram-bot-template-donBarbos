from __future__ import annotations
import copy
from typing import Any

from loguru import logger

from bot.core.config import settings
from bot.utils.emby import get_emby_client


def _normalize_field_paths(field_paths: list[str] | None) -> list[str]:
    return [path.strip() for path in (field_paths or []) if str(path).strip()]


def _expand_policy_exclude_fields(field_paths: list[str] | None) -> list[str]:
    normalized = set(_normalize_field_paths(field_paths))
    if "EnabledDevices" in normalized:
        normalized.add("EnableAllDevices")
    if "EnableAllDevices" in normalized:
        normalized.add("EnabledDevices")
    return list(normalized)


def _merge_template_data(
    payload: dict[str, Any],
    template_data: dict[str, Any],
    exclude_field_paths: set[str],
    parent_path: str = "",
) -> None:
    for key, template_value in template_data.items():
        field_path = f"{parent_path}.{key}" if parent_path else key
        if field_path in exclude_field_paths:
            continue

        current_value = payload.get(key)
        if isinstance(template_value, dict) and isinstance(current_value, dict):
            _merge_template_data(current_value, template_value, exclude_field_paths, field_path)
            continue

        payload[key] = copy.deepcopy(template_value)


def _build_template_payload(
    template_data: dict[str, Any] | None,
    current_data: dict[str, Any] | None,
    exclude_field_paths: list[str] | None = None,
) -> dict[str, Any]:
    payload = copy.deepcopy(current_data or {})
    if not isinstance(template_data, dict):
        return payload

    exclude_set = set(_normalize_field_paths(exclude_field_paths))
    _merge_template_data(payload, template_data, exclude_set)
    return payload


async def sync_users_from_template(
    target_user_ids: list[str],
    template_user_id: str | None = None,
    exclude_policy_fields: list[str] | None = None,
    exclude_configuration_fields: list[str] | None = None,
) -> tuple[int, int, list[str]]:
    """按模板批量同步多个 Emby 用户的 Policy 与 Configuration

    功能说明:
    - 从指定模板用户读取最新 `Configuration` 与 `Policy`
    - 批量覆盖到目标用户
    - 支持通过字段路径排除不想更新的字段，排除字段保留目标用户原值
    - 字段路径支持点号形式，例如 `SubtitleMode`、`MyMediaExcludes.Value`

    输入参数:
    - target_user_ids: 目标 Emby 用户ID列表
    - template_user_id: 模板 Emby 用户ID，可为 None（使用配置中的默认模板）
    - exclude_policy_fields: Policy 中需要排除的字段路径列表
    - exclude_configuration_fields: Configuration 中需要排除的字段路径列表

    返回值:
    - tuple[int, int, list[str]]: (成功数量, 失败数量, 失败详情列表)
    """
    client = get_emby_client()
    if client is None:
        return 0, 0, ["未配置 Emby 连接信息"]

    normalized_target_ids = [str(user_id).strip() for user_id in target_user_ids if str(user_id).strip()]
    if not normalized_target_ids:
        return 0, 0, []

    tid = str(template_user_id or settings.get_emby_template_user_id() or "").strip()
    if not tid:
        return 0, len(normalized_target_ids), ["未提供模板用户ID，且未配置 EMBY_TEMPLATE_USER_ID"]

    try:
        template_user = await client.get_user(tid)
    except Exception as e:  # noqa: BLE001
        return 0, len(normalized_target_ids), [f"模板用户获取失败: {e}"]

    if not template_user or not template_user.get("Id"):
        return 0, len(normalized_target_ids), [f"模板用户不存在: {tid}"]

    template_policy = template_user.get("Policy")
    template_configuration = template_user.get("Configuration")

    if not isinstance(template_policy, dict) and not isinstance(template_configuration, dict):
        return 0, len(normalized_target_ids), [f"模板用户缺少可同步的 Policy/Configuration: {tid}"]

    success_count = 0
    fail_messages: list[str] = []

    for user_id in normalized_target_ids:
        if user_id == tid:
            logger.info(f"⏭️ 跳过模板用户自身: {user_id}")
            continue

        try:
            current_user = await client.get_user(user_id)
            if not current_user or not current_user.get("Id"):
                msg = f"目标用户不存在: {user_id}"
                fail_messages.append(msg)
                logger.warning(f"⚠️ {msg}")
                continue

            if isinstance(template_configuration, dict):
                configuration_payload = _build_template_payload(
                    template_configuration,
                    current_user.get("Configuration"),
                    exclude_configuration_fields,
                )
                await client.update_user_configuration(user_id, configuration_payload)

            if isinstance(template_policy, dict):
                policy_payload = _build_template_payload(
                    template_policy,
                    current_user.get("Policy"),
                    _expand_policy_exclude_fields(exclude_policy_fields),
                )
                await client.update_user_policy(user_id, policy_payload)

            success_count += 1
            logger.info(f"✅ 已按模板同步用户配置: target={user_id} template={tid}")
        except Exception as e:  # noqa: BLE001
            msg = f"同步用户失败 {user_id}: {e}"
            fail_messages.append(msg)
            logger.error(f"❌ {msg}")

    return success_count, len(fail_messages), fail_messages


__all__ = ["sync_users_from_template"]
