"""附件与内部追溯 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import verify_chain, verify_all_chains
from app.core.deps import get_current_user, get_db
from app.services.audit_service import log_modification

router = APIRouter(prefix="/traceability", tags=["附件与内部追溯"])


@router.get("/attachments")
async def list_attachments(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    commission_no: str | None = Query(None),
    task_no: str | None = Query(None),
    package_no: str | None = Query(None),
    attachment_type: str | None = Query(None, description="附件类型：photo/doc/scan/other"),
    search: str | None = Query(None, description="搜索原始文件名"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """附件列表（跨委托/任务包/任务查询）"""
    where = "WHERE 1=1"
    params: dict = {}

    if commission_no:
        where += " AND a.commission_no = :cno"
        params["cno"] = commission_no
    if task_no:
        where += " AND a.task_no = :tno"
        params["tno"] = task_no
    if package_no:
        where += " AND a.package_no = :pkg"
        params["pkg"] = package_no
    if attachment_type:
        where += " AND a.attachment_type = :atype"
        params["atype"] = attachment_type
    if search:
        where += " AND (a.original_name ILIKE :s OR a.description ILIKE :s)"
        params["s"] = f"%{search}%"

    result = await db.execute(
        text(f"""
            SELECT a.id, a.attachment_id, a.commission_no, a.package_no, a.task_no,
                   a.sample_no, a.attachment_type, a.original_name, a.stored_name,
                   a.relative_path, a.sha256, a.captured_at, a.uploader,
                   a.description, a.is_original, a.checkpoint_code, a.checkpoint_label,
                   a.evidence_status, a.created_at
            FROM attachments a
            {where}
            ORDER BY a.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    )
    rows = result.fetchall()
    return [dict(zip(result.keys(), r)) for r in rows]


@router.get("/audit-logs")
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    entity_type: str | None = Query(None, description="实体类型：commission/task/report/user 等"),
    entity_id: str | None = Query(None),
    actor: str | None = Query(None),
    action: str | None = Query(None, description="操作类型：create/update/delete/confirm 等"),
    commission_no: str | None = Query(None, description="按委托编号过滤"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """审计日志列表"""
    where = "WHERE 1=1"
    params: dict = {}

    if entity_type:
        where += " AND al.entity_type = :et"
        params["et"] = entity_type
    if entity_id:
        where += " AND al.entity_id = :eid"
        params["eid"] = entity_id
    if actor:
        where += " AND al.actor = :actor"
        params["actor"] = actor
    if action:
        where += " AND al.action = :act"
        params["act"] = action
    if commission_no:
        where += " AND al.commission_no = :cno"
        params["cno"] = commission_no

    result = await db.execute(
        text(f"""
            SELECT al.id, al.entity_type, al.entity_id, al.actor, al.actor_name,
                   al.actor_role, al.action, al.field_name, al.old_value, al.new_value,
                   al.commission_no, al.created_at
            FROM audit_logs al
            {where}
            ORDER BY al.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    )
    rows = result.fetchall()
    return [dict(zip(result.keys(), r)) for r in rows]


@router.get("/modifications")
async def list_modifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    actor: str | None = Query(None),
    commission_no: str | None = Query(None, description="按委托编号过滤"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """修改日志列表（谁在什么时候改了什么）"""
    where = "WHERE 1=1"
    params: dict = {}

    if entity_type:
        where += " AND ml.entity_type = :et"
        params["et"] = entity_type
    if entity_id:
        where += " AND ml.entity_id = :eid"
        params["eid"] = entity_id
    if actor:
        where += " AND ml.actor = :actor"
        params["actor"] = actor
    if commission_no:
        where += " AND ml.commission_no = :cno"
        params["cno"] = commission_no

    result = await db.execute(
        text(f"""
            SELECT ml.id, ml.entity_type, ml.entity_id, ml.actor, ml.action,
                   ml.field_name, ml.old_value, ml.new_value, ml.reason,
                   ml.commission_no, ml.created_at
            FROM modification_logs ml
            {where}
            ORDER BY ml.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    )
    rows = result.fetchall()
    return [dict(zip(result.keys(), r)) for r in rows]


@router.get("/commission/{commission_no}")
async def trace_commission(
    commission_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """按委托号聚合追溯信息（附件+审计+修改+样品事件）——使用 commission_no 精确匹配"""
    # 附件
    att_result = await db.execute(
        text("SELECT * FROM attachments WHERE commission_no=:c ORDER BY created_at DESC"),
        {"c": commission_no},
    )
    attachments = [dict(zip(att_result.keys(), r)) for r in att_result.fetchall()]

    # 审计日志 — 直接用 commission_no 列精确匹配
    audit_result = await db.execute(
        text("SELECT * FROM audit_logs WHERE commission_no=:c ORDER BY created_at DESC LIMIT 500"),
        {"c": commission_no},
    )
    audits = [dict(zip(audit_result.keys(), r)) for r in audit_result.fetchall()]

    # 修改日志 — 直接用 commission_no 列精确匹配
    mod_result = await db.execute(
        text("SELECT * FROM modification_logs WHERE commission_no=:c ORDER BY created_at DESC LIMIT 500"),
        {"c": commission_no},
    )
    modifications = [dict(zip(mod_result.keys(), r)) for r in mod_result.fetchall()]

    # 样品事件
    se_result = await db.execute(
        text("SELECT * FROM sample_events WHERE commission_no=:c ORDER BY created_at DESC"),
        {"c": commission_no},
    )
    sample_events = [dict(zip(se_result.keys(), r)) for r in se_result.fetchall()]

    # 报告操作记录（也按 commission_no）
    ra_result = await db.execute(
        text("SELECT ra.*, r.commission_no FROM report_actions ra JOIN reports r ON ra.report_no = r.report_no WHERE r.commission_no=:c ORDER BY ra.created_at DESC"),
        {"c": commission_no},
    )
    report_actions = [dict(zip(ra_result.keys(), row)) for row in ra_result.fetchall()]

    return {
        "commission_no": commission_no,
        "attachments": attachments,
        "audit_logs": audits,
        "modifications": modifications,
        "sample_events": sample_events,
        "report_actions": report_actions,
    }


# ── 修改中心：主动修改操作 ──

class ModificationRequest(BaseModel):
    entity_type: str = Field(..., description="实体类型：commission/task/report/sample/record")
    entity_id: str = Field(..., min_length=1, description="实体编号")
    field_name: str = Field(..., min_length=1, description="字段名")
    new_value: str = Field(..., description="新值")
    reason: str = Field(default="", description="修改原因")


@router.post("/modifications", status_code=201)
async def create_modification(
    body: ModificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """在修改中心执行一次字段级修改，记录到 modification_logs + audit_logs"""
    # 获取旧值 — field_name 白名检验证
    table_map = {
        "commission": ("commissions", "commission_no", {
            "client_name", "client_address", "contact", "phone", "notes", "status",
            "report_medium", "conformity_judgment", "delivery_method"}),
        "task": ("tasks", "task_no", {
            "status", "assignee", "reviewer", "detection_location", "experiment"}),
        "report": ("reports", "report_no", {
            "status", "conclusion", "notes", "sample_statement", "tester", "verifier"}),
        "sample": ("samples", "sample_no", {
            "current_location", "current_holder", "status", "condition_note"}),
        "sample_group": ("sample_groups", "group_no", {
            "status", "notes", "condition_note", "storage_area"}),
        "record": ("records", "record_no", {
            "status"}),
        "objection": ("objections", "objection_no", {
            "status", "investigation", "trace_conclusion", "quality_conclusion", "response_body"}),
        "equipment_incident": ("equipment_incidents", "incident_no", {
            "status", "fault_description", "quality_conclusion", "impact_scope"}),
    }
    mapping = table_map.get(body.entity_type)
    if not mapping:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail=f"不支持的实体类型: {body.entity_type}")

    table_name, id_col, allowed_fields = mapping
    if body.field_name not in allowed_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail=f"不允许修改字段 '{body.field_name}'，允许的字段: {', '.join(sorted(allowed_fields))}")

    # 查询旧值（表名和字段名已经白名单验证）
    r = await db.execute(
        text(f"SELECT \"{body.field_name}\" FROM {table_name} WHERE {id_col}=:eid"),
        {"eid": body.entity_id},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                          detail=f"{body.entity_type} '{body.entity_id}' 不存在")

    old_value = str(row[0]) if row[0] is not None else None

    # Skip if no change
    if old_value == body.new_value:
        return {"message": "新旧值相同，无需修改", "old_value": old_value, "new_value": body.new_value}

    # 执行实际更新（白名单验证过的字段名）
    await db.execute(
        text(f"UPDATE {table_name} SET \"{body.field_name}\"=:nv, updated_at=localtimestamp WHERE {id_col}=:eid"),
        {"nv": body.new_value, "eid": body.entity_id},
    )

    # 记录修改日志
    await log_modification(
        db=db,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        user=user,
        field_name=body.field_name,
        old_value=old_value,
        new_value=body.new_value,
        reason=body.reason,
    )

    return {
        "message": "修改已执行并记录",
        "entity_type": body.entity_type,
        "entity_id": body.entity_id,
        "field_name": body.field_name,
        "old_value": old_value,
        "new_value": body.new_value,
        "reason": body.reason,
    }


# ── 审计链验证 ──

@router.get("/audit/verify/{entity_type}/{entity_id}")
async def audit_verify_entity(
    entity_type: str,
    entity_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """验证指定实体的审计链完整性"""
    return await verify_chain(db, entity_type, entity_id)


@router.get("/audit/verify-all-chains")
async def audit_verify_all(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """批量验证所有审计链"""
    return await verify_all_chains(db)
