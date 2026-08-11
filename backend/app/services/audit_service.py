"""统一审计日志服务 — 所有操作写入 audit_logs + modification_logs，支持按委托追溯"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _resolve_commission_no(
    db: AsyncSession, entity_type: str, entity_id: str
) -> str | None:
    """从实体推断 commission_no"""
    if entity_type == "commission":
        return entity_id
    if entity_type in ("report", "report_delivery"):
        r = await db.execute(
            text("SELECT commission_no FROM reports WHERE report_no=:e"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    if entity_type in ("task", "record", "review", "task_package"):
        r = await db.execute(
            text("SELECT commission_no FROM tasks WHERE task_no=:e"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    if entity_type in ("sample_group",):
        r = await db.execute(
            text("SELECT commission_no FROM sample_groups WHERE group_no=:e"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    if entity_type in ("sample", "sample_event"):
        r = await db.execute(
            text("SELECT commission_no FROM samples WHERE sample_no=:e"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    if entity_type in ("objection",):
        r = await db.execute(
            text("SELECT commission_no FROM objections WHERE objection_no=:e"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    if entity_type in ("equipment_incident",):
        r = await db.execute(
            text("SELECT commission_no FROM equipment_incidents WHERE incident_no=:e"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    if entity_type in ("hazardous_waste",):
        r = await db.execute(
            text("SELECT commission_no FROM hazardous_waste_records WHERE disposal_no=:e"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    if entity_type in ("package_loan",):
        r = await db.execute(
            text("SELECT c.commission_no FROM package_loans pl JOIN task_packages tp ON pl.package_no = tp.package_no JOIN tasks t ON tp.package_no = t.package_no WHERE pl.package_no=:e LIMIT 1"),
            {"e": entity_id},
        )
        row = r.fetchone()
        return row[0] if row else None
    return None


def _compute_hash(
    entity_type: str, entity_id: str, actor: str, action: str,
    field_name: str | None, old_value: str | None, new_value: str | None,
    previous_hash: str | None, created_at: str,
) -> str:
    """计算审计条目的 SHA-256 哈希"""
    payload = json.dumps({
        "entity_type": entity_type, "entity_id": entity_id,
        "actor": actor, "action": action,
        "field_name": field_name, "old_value": old_value,
        "new_value": new_value, "previous_hash": previous_hash,
        "created_at": created_at,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


async def write_audit_log(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    actor: str,
    action: str,
    *,
    actor_name: str = "",
    actor_role: str = "",
    commission_no: str | None = None,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
    comment: str | None = None,
    client_time: str | None = None,
    device_id: str | None = None,
    session_token: str | None = None,
) -> int:
    """
    写入一条审计日志（带哈希链）。

    自动解析 commission_no（若未传入），同时写入 modification_logs（如有字段变更）。
    返回新插入的 audit_log id。
    """
    # Resolve commission_no
    if not commission_no:
        commission_no = await _resolve_commission_no(db, entity_type, entity_id)

    now = datetime.now(timezone.utc)
    now_str = now.isoformat()

    # Get previous hash for chain
    prev = await db.execute(
        text("SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
    )
    prev_row = prev.fetchone()
    previous_hash = prev_row[0] if prev_row else "0" * 64

    entry_hash = _compute_hash(
        entity_type, entity_id, actor, action,
        field_name, old_value, new_value, previous_hash, now_str,
    )

    result = await db.execute(
        text("""INSERT INTO audit_logs (
            entity_type, entity_id, actor, actor_name, actor_role,
            action, field_name, old_value, new_value, reason,
            commission_no, client_time, device_id, session_token,
            previous_hash, entry_hash, created_at
        ) VALUES (
            :et, :eid, :a, :an, :ar,
            :act, :fn, :ov, :nv, :r,
            :cn, :ct, :di, :st,
            :ph, :eh, :now
        ) RETURNING id"""),
        {
            "et": entity_type, "eid": entity_id, "a": actor,
            "an": actor_name, "ar": actor_role, "act": action,
            "fn": field_name, "ov": old_value, "nv": new_value,
            "r": reason, "cn": commission_no, "ct": client_time,
            "di": device_id, "st": session_token,
            "ph": previous_hash, "eh": entry_hash, "now": now,
        },
    )
    audit_id = result.fetchone()[0]

    # Also write to modification_logs if there's a field change
    if field_name and (old_value is not None or new_value is not None):
        await db.execute(
            text("""INSERT INTO modification_logs (
                entity_type, entity_id, actor, action,
                field_name, old_value, new_value, reason,
                commission_no, created_at
            ) VALUES (
                :et, :eid, :a, :act,
                :fn, :ov, :nv, :r,
                :cn, :now
            )"""),
            {
                "et": entity_type, "eid": entity_id, "a": actor,
                "act": action, "fn": field_name,
                "ov": old_value, "nv": new_value, "r": reason,
                "cn": commission_no, "now": now,
            },
        )

    # Also write report_actions if entity is a report
    if entity_type == "report":
        c = comment or ""
        if action and not c:
            c = action
        await db.execute(
            text("""INSERT INTO report_actions (report_no, actor, action, comment, created_at)
                VALUES (:r, :a, :act, :c, localtimestamp)"""),
            {"r": entity_id, "a": actor, "act": action, "c": c},
        )

    return audit_id


async def log_operation(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    user: dict,
    action: str,
    *,
    commission_no: str | None = None,
    comment: str | None = None,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
) -> int:
    """
    一站式操作日志快捷函数。
    从 user dict 中提取 actor/actor_name/actor_role。
    """
    return await write_audit_log(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=user.get("username", "system"),
        actor_name=user.get("display_name", user.get("username", "")),
        actor_role=user.get("role", ""),
        action=action,
        commission_no=commission_no,
        comment=comment,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )


async def log_modification(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    user: dict,
    field_name: str,
    old_value: str | None,
    new_value: str | None,
    *,
    commission_no: str | None = None,
    reason: str = "",
    action: str = "update",
) -> int:
    """
    记录一次字段级修改。
    同时写入 audit_logs 和 modification_logs。
    """
    action_label = {
        "update": "修改", "create": "创建", "delete": "删除",
        "confirm": "确认", "approve": "批准", "reject": "退回",
        "void": "作废", "correct": "更正", "revoke": "撤回",
    }.get(action, action)

    return await write_audit_log(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=user.get("username", "system"),
        actor_name=user.get("display_name", user.get("username", "")),
        actor_role=user.get("role", ""),
        action=action_label,
        commission_no=commission_no,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
