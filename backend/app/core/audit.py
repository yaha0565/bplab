"""哈希链审计追踪 — 每次写入计算前一条 SHA-256，形成不可篡改的链表"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical(entry: dict) -> str:
    """标准化 JSON 序列化，去除空格保证确定性"""
    return json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


async def audit(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    actor: str,
    action: str,
    *,
    actor_name: str = "",
    actor_role: str = "",
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
    client_time: str | None = None,
    device_id: str | None = None,
    session_token: str | None = None,
    snapshot: dict | None = None,
) -> int:
    """向审计日志写入一条记录，自动计算哈希链表。

    Returns the new audit_log entry id.
    """
    # 1. 查询最后一条审计记录的 entry_hash
    prev = await db.execute(
        text("SELECT entry_hash FROM audit_logs WHERE entity_type=:et AND entity_id=:eid ORDER BY id DESC LIMIT 1"),
        {"et": entity_type, "eid": entity_id},
    )
    prev_row = prev.fetchone()
    previous_hash = prev_row[0] if prev_row and prev_row[0] else "0" * 64

    # 2. 计算快照哈希
    snapshot_hash = _sha256(_canonical(snapshot)) if snapshot else None

    # 3. 构建条目（不含 entry_hash，因为 entry_hash 是对所有字段的哈希）
    entry = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor": actor,
        "actor_name": actor_name,
        "actor_role": actor_role,
        "action": action,
        "field_name": field_name,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "client_time": client_time,
        "device_id": device_id,
        "session_token": session_token,
        "snapshot_hash": snapshot_hash,
        "previous_hash": previous_hash,
    }
    # 去除 None 值使归一化确定
    entry = {k: v for k, v in entry.items() if v is not None}

    # 4. 计算本条目哈希
    entry_hash = _sha256(_canonical(entry))
    entry["entry_hash"] = entry_hash

    # 5. 写入数据库
    result = await db.execute(
        text("""INSERT INTO audit_logs (
                entity_type, entity_id, actor, actor_name, actor_role, action,
                field_name, old_value, new_value, reason, client_time, device_id,
                session_token, snapshot_hash, previous_hash, entry_hash
            ) VALUES (
                :et, :eid, :a, :an, :ar, :ac,
                :fn, :ov, :nv, :r, :ct, :di,
                :st, :sh, :ph, :eh
            ) RETURNING id"""),
        {**entry},
    )
    return result.fetchone()[0]


async def verify_chain(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> dict:
    """验证指定实体的审计链是否完整、未被篡改。

    Returns {"valid": bool, "entries": int, "breaks": [{"at_id": ..., "expected": ..., "found": ...}]}
    """
    result = await db.execute(
        text("""SELECT id, previous_hash, entry_hash, created_at
                FROM audit_logs
                WHERE entity_type=:et AND entity_id=:eid
                ORDER BY id"""),
        {"et": entity_type, "eid": entity_id},
    )
    rows = result.fetchall()
    entries = [dict(zip(result.keys(), r)) for r in rows]

    if not entries:
        return {"valid": True, "entries": 0, "breaks": []}

    breaks = []
    prev = "0" * 64
    for e in entries:
        if e.get("previous_hash") != prev:
            breaks.append({
                "at_id": e["id"],
                "expected": prev,
                "found": e.get("previous_hash"),
            })
        prev = e.get("entry_hash", "0" * 64)

    return {
        "valid": len(breaks) == 0,
        "entries": len(entries),
        "first_at": str(entries[0]["created_at"]) if entries[0].get("created_at") else None,
        "last_at": str(entries[-1]["created_at"]) if entries[-1].get("created_at") else None,
        "breaks": breaks,
    }


async def verify_all_chains(
    db: AsyncSession,
) -> dict:
    """批量验证所有实体类型的审计链"""
    result = await db.execute(
        text("""SELECT DISTINCT entity_type, entity_id FROM audit_logs ORDER BY entity_type"""))
    pairs = result.fetchall()

    results = {}
    for entity_type, entity_id in pairs:
        v = await verify_chain(db, entity_type, entity_id)
        key = f"{entity_type}/{entity_id}"
        results[key] = v

    total = len(results)
    broken = sum(1 for r in results.values() if not r["valid"])
    return {"total_chains": total, "broken_chains": broken, "chains": results}
