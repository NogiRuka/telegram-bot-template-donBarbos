"""机器人代执行群组管理操作时的短期操作者上下文。"""

import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModerationActor:
    """一次机器人代执行管理操作的真实发起人。"""

    user_id: int
    full_name: str
    action: str
    expires_at: float


_CONTEXT_TTL_SECONDS = 60.0
_pending_actions: dict[tuple[int, int], ModerationActor] = {}


def _prune_expired_actions(current_time: float) -> None:
    """清理已过期的管理操作上下文。"""
    expired_keys = [
        key
        for key, actor in _pending_actions.items()
        if actor.expires_at <= current_time
    ]
    for key in expired_keys:
        _pending_actions.pop(key, None)


def register_moderation_action(
    chat_id: int,
    target_user_id: int,
    actor_user_id: int,
    actor_full_name: str,
    action: str,
) -> None:
    """登记即将由机器人代执行的群组管理操作。"""
    current_time = time.monotonic()
    _prune_expired_actions(current_time)
    _pending_actions[(chat_id, target_user_id)] = ModerationActor(
        user_id=actor_user_id,
        full_name=actor_full_name,
        action=action,
        expires_at=current_time + _CONTEXT_TTL_SECONDS,
    )


def consume_moderation_action(chat_id: int, target_user_id: int) -> ModerationActor | None:
    """取得并移除一次尚未过期的群组管理操作上下文。"""
    current_time = time.monotonic()
    _prune_expired_actions(current_time)
    return _pending_actions.pop((chat_id, target_user_id), None)


def discard_moderation_action(chat_id: int, target_user_id: int) -> None:
    """在代执行操作失败时丢弃对应上下文。"""
    _pending_actions.pop((chat_id, target_user_id), None)
