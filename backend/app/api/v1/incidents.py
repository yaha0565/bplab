"""设备故障处置 API — 报告→隔离→评估→批准 4步生命周期"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.encoding_rules import china_now, china_today

router = APIRouter(prefix="/incidents", tags=["设备故障处置"])


# ── Pydantic models ──

class CreateIncidentRequest(BaseModel):
    task_no: str
    equipment_no: str
    fault_type: str = ""
    fault_description: str
    error_code: str = ""
    current_stage: str = ""
    completed_steps: str = ""
    collected_data: str = ""
    sample_condition: str = ""
    risk_types: list[str] = []
    immediate_actions: list[str] = []


class IsolateRequest(BaseModel):
    isolation_location: str
    storage_requirements: str
    receiver_note: str = ""


class AssessRequest(BaseModel):
    sample_validity: str  # 可稳定保存并整套重做 / 样品不可逆失效 / 需更换备用设备整套重做
    quality_conclusion: str
    impact_scope: str
    quality_note: str = ""


class ApproveRequest(BaseModel):
    recovery_route: str  # 样品失效等待重新送样 / 原设备维修核查合格后整套重做 / 改用备用合格设备整套重做
    performance_check_result: str
    admin_note: str
    backup_equipment_no: str = ""


# ── Helpers ──

async def _notify(db: AsyncSession, recipients: list[str], title: str, body: str,
                   entity_type: str, entity_id: str):
    """发送通知给一批用户"""
    for r in recipients:
        await db.execute(
            text("""INSERT INTO notifications (recipient, title, message, entity_type, entity_id)
                    VALUES (:r, :t, :b, :et, :eid)"""),
            {"r": r, "t": title, "b": body, "et": entity_type, "eid": entity_id},
        )


async def _audit(db: AsyncSession, entity_type: str, entity_id: str, actor: str,
                 action: str, old_value: str = None, new_value: str = None,
                 field_name: str = None):
    """记录审计日志（基础版，哈希链升级在 Phase 4C）"""
    await db.execute(
        text("""INSERT INTO audit_logs (entity_type, entity_id, actor, action, field_name,
                old_value, new_value, created_at)
                VALUES (:et, :eid, :a, :act, :fn, :ov, :nv, now())"""),
        {"et": entity_type, "eid": entity_id, "a": actor, "act": action,
         "fn": field_name, "ov": old_value, "nv": new_value},
    )


def _next_incident_no(now: datetime = None) -> str:
    """EQI + YYYYMMDD + -NNN"""
    dt = now or china_now()
    return f"EQI{dt.strftime('%Y%m%d')}"


# ── Endpoints ──

@router.get("")
async def list_incidents(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """设备故障列表（按角色过滤）"""
    role = user.get("role", "")
    username = user.get("username", "")

    where = "WHERE 1=1"
    params: dict = {}
    if role == "实验员":
        where += " AND (ei.created_by=:u OR t.assignee=:u)"
        params["u"] = username
    elif role == "复核员":
        where += " AND t.reviewer=:u"
        params["u"] = username

    result = await db.execute(
        text(f"""
            SELECT ei.*, t.experiment, t.assignee, t.reviewer,
                   u.display_name AS reporter_name
            FROM equipment_incidents ei
            JOIN tasks t ON t.task_no = ei.task_no
            LEFT JOIN users u ON u.username = ei.created_by
            {where}
            ORDER BY ei.created_at DESC, ei.incident_no DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    )
    return [dict(zip(result.keys(), r)) for r in result.fetchall()]


@router.get("/{incident_no}")
async def get_incident(
    incident_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """故障单详情 + 操作历史"""
    inc = await db.execute(
        text("SELECT * FROM equipment_incidents WHERE incident_no=:n"),
        {"n": incident_no},
    )
    row = inc.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故障单不存在")

    actions = await db.execute(
        text("""SELECT a.*, u.display_name AS actor_name, u.role AS actor_role
                FROM equipment_incident_actions a
                LEFT JOIN users u ON u.username = a.actor
                WHERE a.incident_no=:n ORDER BY a.id"""),
        {"n": incident_no},
    )
    return {
        "incident": dict(zip(inc.keys(), row)),
        "actions": [dict(zip(actions.keys(), a)) for a in actions.fetchall()],
    }


@router.post("", status_code=201)
async def create_incident(
    body: CreateIncidentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """实验员报告设备故障，冻结记录/停用设备/隔离样品"""
    actor = user["username"]
    if user.get("role") != "实验员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有实验员可报告设备故障")

    # 验证任务
    t = await db.execute(
        text("SELECT * FROM tasks WHERE task_no=:tn"), {"tn": body.task_no})
    task_row = t.fetchone()
    if not task_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实验任务不存在")
    task = dict(zip(t.keys(), task_row))
    if task.get("assignee") != actor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能对自己负责的任务报告设备故障")
    if task.get("status") not in ("检测中", "退回修改"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前任务状态不能启动设备故障中断")

    # 检查是否有未关闭的故障单
    existing = await db.execute(
        text("""SELECT incident_no FROM equipment_incidents
                WHERE task_no=:tn AND status NOT IN ('已关闭','样品失效待重新送样')"""),
        {"tn": body.task_no})
    if existing.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该实验已有未关闭的设备故障处置")

    # 验证设备
    eq = await db.execute(
        text("SELECT * FROM equipment_registry WHERE management_no=:mn"),
        {"mn": body.equipment_no})
    eq_row = eq.fetchone()
    if not eq_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故障设备不存在")
    equipment = dict(zip(eq.keys(), eq_row))

    if not body.fault_description.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="请填写设备故障现象")

    # 验证应急动作
    required_actions = {"终止试验动作", "保护故障现场", "样品保持原位并等待隔离"}
    if not required_actions.issubset(set(body.immediate_actions)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="请确认已完成终止试验、保护现场和样品隔离准备")

    # 生成编号
    prefix = _next_incident_no()
    seq_result = await db.execute(
        text("""SELECT incident_no FROM equipment_incidents
                WHERE incident_no LIKE :pat ORDER BY incident_no DESC LIMIT 1"""),
        {"pat": f"{prefix}-%"},
    )
    last = seq_result.fetchone()
    seq = int(last[0].rsplit("-", 1)[1]) + 1 if last else 1
    incident_no = f"{prefix}-{seq:03d}"

    ts = china_now().isoformat()
    sample_nos = json.loads(task.get("sample_nos") or "[]") if isinstance(task.get("sample_nos"), str) else (task.get("sample_nos") or [])

    # 冻结记录（如果有的话）
    rec_result = await db.execute(
        text("SELECT version, payload FROM records WHERE task_no=:tn ORDER BY version DESC LIMIT 1"),
        {"tn": body.task_no})
    frozen_version = None
    record = rec_result.fetchone()
    if record:
        frozen_version = record[0]
        # 更新记录状态为故障中断作废
        await db.execute(
            text("""UPDATE records SET status='故障中断作废', updated_at=now()
                    WHERE task_no=:tn AND version=:v"""),
            {"tn": body.task_no, "v": frozen_version},
        )

    # 创建故障单
    await db.execute(
        text("""INSERT INTO equipment_incidents (
                incident_no, task_no, package_no, commission_no, group_id,
                equipment_no, equipment_name, reporter, occurred_at,
                fault_type, fault_description, error_code, current_stage,
                completed_steps, collected_data, sample_condition,
                risk_types, immediate_actions, involved_samples,
                frozen_record_version, status, created_at, updated_at
            ) VALUES (
                :ino, :tn, :pkg, :cno, :gid, :eno, :enm, :rpt, :ts,
                :ft, :fd, :ec, :cs, :cps, :cd, :sc,
                :rt::jsonb, :ia::jsonb, :isamp::jsonb,
                :fv, '待样品隔离', now(), now()
            )"""),
        {
            "ino": incident_no, "tn": body.task_no,
            "pkg": task.get("package_no", ""), "cno": task.get("commission_no", ""),
            "gid": task.get("group_id"), "eno": body.equipment_no,
            "enm": equipment.get("equipment_name", ""), "rpt": actor, "ts": ts,
            "ft": body.fault_type, "fd": body.fault_description,
            "ec": body.error_code, "cs": body.current_stage,
            "cps": body.completed_steps, "cd": body.collected_data,
            "sc": body.sample_condition,
            "rt": json.dumps(body.risk_types, ensure_ascii=False),
            "ia": json.dumps(body.immediate_actions, ensure_ascii=False),
            "isamp": json.dumps(sample_nos, ensure_ascii=False),
            "fv": frozen_version,
        },
    )

    # 记录操作
    await db.execute(
        text("""INSERT INTO equipment_incident_actions (incident_no, actor, action, comment, created_at)
                VALUES (:ino, :a, '实验员报告设备故障并中断试验', '系统冻结当前记录、停用设备并隔离样品', now())"""),
        {"ino": incident_no, "a": actor},
    )

    # 更新任务/任务包/样品组状态
    await db.execute(
        text("""UPDATE tasks SET status='设备故障中断',
                experiment_ended_at=COALESCE(experiment_ended_at, now()), updated_at=now()
                WHERE task_no=:tn"""),
        {"tn": body.task_no},
    )
    await db.execute(
        text("UPDATE task_packages SET status='设备故障中断', updated_at=now() WHERE package_no=:pn"),
        {"pn": task.get("package_no")},
    )
    await db.execute(
        text("UPDATE sample_groups SET status='故障隔离', updated_at=now() WHERE id=:gid"),
        {"gid": task.get("group_id")},
    )

    # 停用设备
    await db.execute(
        text("""UPDATE equipment_registry SET enabled=FALSE, lifecycle_status='停用',
                status_note=:sn, updated_at=now() WHERE management_no=:mn"""),
        {"sn": f"{incident_no} 设备故障试验中断，禁止使用", "mn": body.equipment_no},
    )

    # 标记附件
    await db.execute(
        text("""UPDATE attachments SET evidence_status='设备故障中断留档'
                WHERE task_no=:tn AND evidence_status='有效'"""),
        {"tn": body.task_no},
    )

    # 隔离样品
    for sno in sample_nos:
        old = await db.execute(
            text("SELECT status, current_location FROM samples WHERE sample_no=:sn"),
            {"sn": sno})
        old_row = old.fetchone()
        await db.execute(
            text("""UPDATE samples SET status='故障隔离', current_location='待确认隔离位置',
                    current_holder='', updated_at=now() WHERE sample_no=:sn"""),
            {"sn": sno},
        )
        await db.execute(
            text("""INSERT INTO sample_events (sample_no, actor, action, from_status, to_status,
                    from_location, to_location, details, created_at)
                    VALUES (:sn, :a, '设备故障中断隔离', :fs, '故障隔离', :fl, '待确认隔离位置', :det, now())"""),
            {"sn": sno, "a": actor,
             "fs": old_row[0] if old_row else "", "fl": old_row[1] if old_row else "",
             "det": f"故障单:{incident_no};设备:{body.equipment_no}"},
        )

    # 通知样品管理员、质量负责人、管理员
    admins = await db.execute(text("SELECT username FROM users WHERE role IN ('样品管理员','质量负责人','管理员') AND enabled IS TRUE"))
    admin_list = [r[0] for r in admins.fetchall()]
    await _notify(db, admin_list, "设备故障导致实验中断",
                  f"{body.task_no} 因 {body.equipment_no} 发生故障，已冻结原始记录并隔离样品。故障单：{incident_no}",
                  "equipment_incident", incident_no)

    await _audit(db, "equipment_incident", incident_no, actor, "启动设备故障中断处置",
                 new_value=json.dumps({"equipment_no": body.equipment_no, "task_no": body.task_no}, ensure_ascii=False))

    return {"incident_no": incident_no, "status": "待样品隔离", "message": "设备故障已报告，等待样品管理员隔离确认"}


@router.put("/{incident_no}/isolate")
async def isolate_incident(
    incident_no: str,
    body: IsolateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """样品管理员确认样品隔离"""
    actor = user["username"]
    if user.get("role") != "样品管理员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有样品管理员可以确认样品隔离")

    inc = await db.execute(
        text("SELECT * FROM equipment_incidents WHERE incident_no=:n"), {"n": incident_no})
    row = inc.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故障单不存在")
    item = dict(zip(inc.keys(), row))
    if item.get("status") != "待样品隔离":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前故障单不在待样品隔离状态")

    if not body.isolation_location.strip() or not body.storage_requirements.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="隔离位置和保存要求均不能为空")

    await db.execute(
        text("""UPDATE equipment_incidents SET status='待质量评估',
                isolation_location=:loc, storage_requirements=:sr, receiver_note=:rn,
                receiver_by=:a, receiver_at=now(), updated_at=now()
                WHERE incident_no=:n"""),
        {"n": incident_no, "loc": body.isolation_location.strip(),
         "sr": body.storage_requirements.strip(), "rn": body.receiver_note.strip(), "a": actor},
    )

    # 更新样品隔离位置
    involved = json.loads(item.get("involved_samples") or "[]") if isinstance(item.get("involved_samples"), str) else (item.get("involved_samples") or [])
    for sno in involved:
        await db.execute(
            text("""UPDATE samples SET status='故障隔离', current_location=:loc,
                    current_holder=:a, updated_at=now() WHERE sample_no=:sn"""),
            {"loc": body.isolation_location.strip(), "a": actor, "sn": sno},
        )
        await db.execute(
            text("""INSERT INTO sample_events (sample_no, actor, action, from_status, to_status,
                    from_location, to_location, details, created_at)
                    VALUES (:sn, :a, '确认故障隔离位置', '故障隔离', '故障隔离', '', :loc, :det, now())"""),
            {"sn": sno, "a": actor, "loc": body.isolation_location.strip(),
             "det": f"故障单:{incident_no};保存要求:{body.storage_requirements}"},
        )

    await db.execute(
        text("""INSERT INTO equipment_incident_actions (incident_no, actor, action, comment, created_at)
                VALUES (:n, :a, '确认样品隔离', :cmt, now())"""),
        {"n": incident_no, "a": actor,
         "cmt": f"位置:{body.isolation_location};保存要求:{body.storage_requirements};{body.receiver_note}"},
    )

    # 通知质量负责人
    quality_users = await db.execute(
        text("SELECT username FROM users WHERE role='质量负责人' AND enabled IS TRUE"))
    qlist = [r[0] for r in quality_users.fetchall()]
    await _notify(db, qlist, "设备故障待质量评估",
                  f"{incident_no} 已完成样品隔离，请评估数据、样品有效性和影响范围。",
                  "equipment_incident", incident_no)

    await _audit(db, "equipment_incident", incident_no, actor, "确认样品隔离",
                 new_value=body.isolation_location)

    return {"message": "样品隔离已确认", "status": "待质量评估"}


@router.put("/{incident_no}/assess")
async def assess_incident(
    incident_no: str,
    body: AssessRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """质量负责人提交质量评估"""
    actor = user["username"]
    if user.get("role") != "质量负责人":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有质量负责人可以提交质量评估")

    inc = await db.execute(
        text("SELECT * FROM equipment_incidents WHERE incident_no=:n"), {"n": incident_no})
    row = inc.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故障单不存在")
    item = dict(zip(inc.keys(), row))
    if item.get("status") != "待质量评估":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前故障单不在待质量评估状态")

    valid_options = ("可稳定保存并整套重做", "样品不可逆失效", "需更换备用设备整套重做")
    if body.sample_validity not in valid_options:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"sample_validity 必须是: {', '.join(valid_options)}")

    if not body.quality_conclusion.strip() or not body.impact_scope.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="质量调查结论和影响范围不能为空")

    await db.execute(
        text("""UPDATE equipment_incidents SET status='待管理员批准',
                sample_validity=:sv, quality_conclusion=:qc, impact_scope=:isc,
                quality_note=:qn, quality_by=:a, quality_at=now(), updated_at=now()
                WHERE incident_no=:n"""),
        {"n": incident_no, "sv": body.sample_validity, "qc": body.quality_conclusion.strip(),
         "isc": body.impact_scope.strip(), "qn": body.quality_note.strip(), "a": actor},
    )

    await db.execute(
        text("""INSERT INTO equipment_incident_actions (incident_no, actor, action, comment, created_at)
                VALUES (:n, :a, '提交质量评估', :cmt, now())"""),
        {"n": incident_no, "a": actor,
         "cmt": f"{body.sample_validity};影响范围:{body.impact_scope};{body.quality_conclusion}"},
    )

    # 通知管理员
    admins = await db.execute(
        text("SELECT username FROM users WHERE role='管理员' AND enabled IS TRUE"))
    alist = [r[0] for r in admins.fetchall()]
    await _notify(db, alist, "设备故障待技术批准",
                  f"{incident_no} 已完成质量评估，请决定恢复路径。",
                  "equipment_incident", incident_no)

    await _audit(db, "equipment_incident", incident_no, actor, "提交质量评估",
                 new_value=body.sample_validity)

    return {"message": "质量评估已提交", "status": "待管理员批准"}


@router.put("/{incident_no}/approve")
async def approve_incident(
    incident_no: str,
    body: ApproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """管理员技术批准恢复路径"""
    actor = user["username"]
    if user.get("role") != "管理员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员可以执行技术批准")

    inc = await db.execute(
        text("SELECT * FROM equipment_incidents WHERE incident_no=:n"), {"n": incident_no})
    row = inc.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="故障单不存在")
    item = dict(zip(inc.keys(), row))

    if item.get("status") != "待管理员批准":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前故障单不在待管理员批准状态")

    allowed = ("样品失效，等待客户重新送样",
               "原设备维修核查合格后整套重做",
               "改用备用合格设备整套重做")
    if body.recovery_route not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"recovery_route 必须是: {' / '.join(allowed)}")

    if not body.admin_note.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="技术批准意见不能为空")

    if body.recovery_route != allowed[0] and "核查合格" not in body.performance_check_result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="设备性能核查未合格，不能批准恢复实验")

    if body.recovery_route == allowed[2]:
        if not body.backup_equipment_no:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="请指定备用合格设备编号")
        bk = await db.execute(
            text("SELECT * FROM equipment_registry WHERE management_no=:mn AND enabled IS TRUE AND lifecycle_status='启用'"),
            {"mn": body.backup_equipment_no})
        if not bk.fetchone():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="备用设备不存在、已停用或未启用")
        if body.backup_equipment_no == item.get("equipment_no"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="备用设备不能与故障设备相同")

    # 样品失效路径：不恢复实验
    if body.recovery_route == allowed[0]:
        new_status = "样品失效待重新送样"
        await db.execute(
            text("""UPDATE equipment_incidents SET status=:st,
                    recovery_route=:rr, performance_check_result=:pcr, admin_note=:an,
                    approved_by=:a, approved_at=now(), closed_at=now(), updated_at=now()
                    WHERE incident_no=:n"""),
            {"n": incident_no, "st": new_status, "rr": body.recovery_route,
             "pcr": body.performance_check_result, "an": body.admin_note.strip(), "a": actor},
        )
        # 更新任务包状态
        await db.execute(
            text("UPDATE task_packages SET status='样品失效待重新送样', updated_at=now() WHERE package_no=:pn"),
            {"pn": item.get("package_no")},
        )
    else:
        new_status = "已关闭"
        # 恢复设备
        eq_to_restore = body.backup_equipment_no if body.recovery_route == allowed[2] else item.get("equipment_no")
        if body.recovery_route == allowed[1]:
            # 原设备维修核查合格
            await db.execute(
                text("""UPDATE equipment_registry SET enabled=TRUE, lifecycle_status='启用',
                        status_note='维修核查合格，恢复使用', updated_at=now()
                        WHERE management_no=:mn"""),
                {"mn": eq_to_restore},
            )

        # 为整套重做创建新版本草稿
        rec_result = await db.execute(
            text("SELECT version FROM records WHERE task_no=:tn ORDER BY version DESC LIMIT 1"),
            {"tn": item.get("task_no")})
        latest_ver = rec_result.fetchone()
        new_version = (latest_ver[0] + 1) if latest_ver else 1

        await db.execute(
            text("""INSERT INTO records (task_no, version, status, owner, payload, created_at, updated_at)
                    VALUES (:tn, :v, '草稿', :ow, '{}'::jsonb, now(), now())"""),
            {"tn": item.get("task_no"), "v": new_version, "ow": item.get("reporter") or item.get("created_by")},
        )

        # 恢复任务和任务包状态
        await db.execute(
            text("""UPDATE tasks SET status='退回修改', experiment_ended_at=NULL, updated_at=now()
                    WHERE task_no=:tn"""),
            {"tn": item.get("task_no")},
        )
        await db.execute(
            text("UPDATE task_packages SET status='检测中', updated_at=now() WHERE package_no=:pn"),
            {"pn": item.get("package_no")},
        )
        await db.execute(
            text("UPDATE sample_groups SET status='检测中', updated_at=now() WHERE id=:gid"),
            {"gid": item.get("group_id")},
        )

        await db.execute(
            text("""UPDATE equipment_incidents SET status=:st,
                    recovery_route=:rr, performance_check_result=:pcr,
                    backup_equipment_no=:ben, admin_note=:an,
                    approved_by=:a, approved_at=now(), resumed_record_version=:rv,
                    closed_at=now(), updated_at=now()
                    WHERE incident_no=:n"""),
            {"n": incident_no, "st": new_status, "rr": body.recovery_route,
             "pcr": body.performance_check_result, "ben": body.backup_equipment_no,
             "an": body.admin_note.strip(), "a": actor, "rv": new_version},
        )

    await db.execute(
        text("""INSERT INTO equipment_incident_actions (incident_no, actor, action, comment, created_at)
                VALUES (:n, :a, '技术批准恢复', :cmt, now())"""),
        {"n": incident_no, "a": actor,
         "cmt": f"{body.recovery_route};{body.admin_note}"},
    )

    await _audit(db, "equipment_incident", incident_no, actor, "技术批准恢复",
                 new_value=body.recovery_route)

    return {"message": "技术批准已完成", "status": new_status, "recovery_route": body.recovery_route}
