from __future__ import annotations

import json
from typing import Any

from bot.database.models.emby_user import EmbyUserModel
from bot.database.models.emby_user_history import EmbyUserHistoryModel
from bot.utils.datetime import parse_formatted_datetime, parse_iso_datetime


def _canon_json(obj: Any) -> str:
    """生成规范化 JSON 字符串用于比较

    功能说明:
    - 将 Python 对象转换为排序键且紧凑的 JSON 字符串
    - 解决字典键顺序、数字表现形式等导致的误判

    输入参数:
    - obj: 任意可 JSON 序列化的对象

    返回值:
    - str: 规范化后的 JSON 字符串
    """
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:  # noqa: BLE001
        return str(obj)


def detect_and_update_emby_user(
    model: EmbyUserModel,
    new_user_dto: dict[str, Any],
    session: Any,
    force_update: bool = False,
    extra_remark: str | None = None,
) -> bool:
    """检测并更新 Emby 用户字段

    功能说明:
    - 比较新旧 UserDto 检测字段变更
    - 自动生成变更说明并写入 History 表
    - 更新主表字段

    输入参数:
    - model: 当前数据库中的 EmbyUserModel 实例
    - new_user_dto: 最新的 Emby UserDto 字典
    - session: SQLAlchemy 会话
    - force_update: 是否强制更新(即使 UserDto 未变), 默认为 False
    - extra_remark: 附加的备注信息(如 "系统自动封禁")

    返回值:
    - bool: 是否发生了更新
    """
    old_dto = model.user_dto or {}

    # 如果没有强制更新且 JSON 内容一致，则无需更新
    if not force_update and _canon_json(old_dto) == _canon_json(new_user_dto):
        return False

    # 解析新字段
    name = str(new_user_dto.get("Name") or "")
    
    # 尝试解析时间，优先使用 ISO 格式解析，因为 Emby API 返回的是 ISO 格式
    # 但如果是从本地数据恢复，可能是 formatted 格式，这里主要处理 API 返回数据
    date_created = parse_iso_datetime(new_user_dto.get("DateCreated"))
    last_login_date = parse_iso_datetime(new_user_dto.get("LastLoginDate"))
    last_activity_date = parse_iso_datetime(new_user_dto.get("LastActivityDate"))

    # 检测具体哪些字段变化了
    changed_fields: list[str] = []
    
    old_name = model.name
    old_dc = model.date_created
    old_ll = model.last_login_date
    old_la = model.last_activity_date
    
    # 保存旧的关键字段用于历史记录
    old_remark = model.remark
    old_password_hash = model.password_hash

    if name != old_name:
        changed_fields.append(f"name 从 {old_name} 更新为 {name}")
    
    # 时间比较需要注意 None 的情况
    if date_created != old_dc:
        changed_fields.append(f"date_created 从 {old_dc} 更新为 {date_created}")
    if last_login_date != old_ll:
        changed_fields.append(f"last_login_date 从 {old_ll} 更新为 {last_login_date}")
    if last_activity_date != old_la:
        changed_fields.append(f"last_activity_date 从 {old_la} 更新为 {last_activity_date}")

    # 生成备注
    remark_parts = []
    if extra_remark:
        remark_parts.append(extra_remark)
    if changed_fields:
        remark_parts.append("; ".join(changed_fields))
    elif not extra_remark:
        remark_parts.append("user_dto 有其他字段变化")
    
    new_remark = " | ".join(remark_parts)

    # 保存旧数据到历史表
    history_entry = EmbyUserHistoryModel(
        emby_user_id=model.emby_user_id,
        name=old_name,
        password_hash=old_password_hash,
        date_created=model.date_created,
        last_login_date=model.last_login_date,
        last_activity_date=model.last_activity_date,
        user_dto=old_dto,
        extra_data=model.extra_data,
        action="update" if not extra_remark else "system_update",
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=model.created_by,
        updated_by=model.updated_by,
        is_deleted=model.is_deleted,
        deleted_at=model.deleted_at,
        deleted_by=model.deleted_by,
        remark=old_remark,
    )
    session.add(history_entry)

    # 更新主表字段
    model.remark = new_remark
    model.name = name
    model.user_dto = new_user_dto
    model.date_created = date_created
    model.last_login_date = last_login_date
    model.last_activity_date = last_activity_date

    return True
