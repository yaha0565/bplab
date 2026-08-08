"""客户异议 API — 登记→调查→重测→回复→归档完整生命周期"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.encoding_rules import china_now

router = APIRouter(prefix="/objections", tags=["客户异议"])


# ── Pydantic models ──

class RegisterObjectionRequest(BaseModel):
    report_no: str
    client_name: str = ""
    contact: str = ""
    description: str
    evidence_note: str = ""
    disputed_items: str = ""  # 顿号分隔的争议检测项目
    involved_samples: str = ""
    application_channel: str = ""


class InvestigateRequest(BaseModel):
    pathway: str  # "是我方问题" or "样品问题"
    investigation: str
    trace_conclusion: str
    quality_evidence: str = ""
    quality_method_check: str = ""
    quality_equipment_check: str = ""
    quality_environment_check: str = ""
    quality_operation_check: str = ""
    quality_calculation_check: str = ""
    impact_scope: str = ""
    treatment_suggestion: str = ""


class RetestDecisionRequest(BaseModel):
    decision: str  # "需要重测" or "不需要重测"
    note: str = ""


class DispatchRetestRequest(BaseModel):
    assignee: str
    selected_sample_nos: list[str] = []


class PrepareResponseRequest(BaseModel):
    response_text: str
    response_method: str = ""


class SendResponseRequest(BaseModel):
    note: str = ""
    response_method: str = ""


# ── Helpers ──

def _next_objection_no(now: datetime = None) -> str:
    dt = now or china_now()
    return f"Y{dt.strftime('%Y%m%d')}"


async def _notify(db: AsyncSession, recipients: list[str], title: str, body: str,
                   entity_type: str, entity_id: str):
    for r in recipients:
        await db.execute(
            text("""INSERT INTO notifications (recipient, title, message, entity_type, entity_id)
                    VALUES (:r, :t, :b, :et, :eid)"""),
            {"r": r, "t": title, "b": body, "et": entity_type, "eid": entity_id},
        )


async def _auto_match_user(db: AsyncSession, role: str, exclude: set = None) -> str:
    exclude = exclude or set()
    result = await db.execute(
        text("SELECT username FROM users WHERE role=:r AND enabled IS TRUE ORDER BY username"),
        {"r": role},
    )
    for row in result.fetchall():
        if row[0] not in exclude:
            return row[0]
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"没有可用的{role}")


# ── Endpoints ──

@router.get("")
async def list_objections(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """客户异议列表（按角色过滤）"""
    role = user.get("role", "")
    username = user.get("username", "")
    if role == "质量负责人":
        result = await db.execute(
            text("SELECT * FROM objections WHERE quality_inspector=:u ORDER BY updated_at DESC"),
            {"u": username},
        )
    else:
        result = await db.execute(
            text("SELECT * FROM objections ORDER BY updated_at DESC"),
        )
    return [dict(zip(result.keys(), r)) for r in result.fetchall()]


@router.get("/{objection_no}")
async def get_objection(
    objection_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """异议详情+操作历史"""
    obj = await db.execute(
        text("SELECT * FROM objections WHERE objection_no=:n"), {"n": objection_no})
    row = obj.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异议不存在")
    actions = await db.execute(
        text("SELECT * FROM objection_actions WHERE objection_no=:n ORDER BY id"),
        {"n": objection_no},
    )
    return {
        "objection": dict(zip(obj.keys(), row)),
        "actions": [dict(zip(actions.keys(), a)) for a in actions.fetchall()],
    }


@router.post("", status_code=201)
async def register_objection(
    body: RegisterObjectionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """样品管理员登记客户异议"""
    actor = user["username"]
    if user.get("role") != "样品管理员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有样品管理员可以录入客户异议")

    # 验证报告
    rep = await db.execute(
        text("SELECT * FROM reports WHERE report_no=:r"), {"r": body.report_no})
    report_row = rep.fetchone()
    if not report_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    report = dict(zip(rep.keys(), report_row))
    if report.get("status") != "已发布":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能对已经签发的检验报告登记异议")

    if not body.description.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="客户异议内容不能为空")

    # 验证争议项目
    disputed = [x.strip() for x in body.disputed_items.replace("，", "、").split("、") if x.strip()]
    if not disputed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="至少选择一个争议检测项目")

    # 匹配质量负责人
    inspector = await _auto_match_user(db, "质量负责人")

    # 生成编号
    prefix = _next_objection_no()
    seq_result = await db.execute(
        text("SELECT objection_no FROM objections WHERE objection_no LIKE :pat ORDER BY objection_no DESC LIMIT 1"),
        {"pat": f"{prefix}%"},
    )
    last = seq_result.fetchone()
    seq = int(last[0][-3:]) + 1 if last else 1
    objection_no = f"{prefix}{seq:03d}"

    await db.execute(
        text("""INSERT INTO objections (
                objection_no, report_no, commission_no, client_name, contact,
                description, evidence_note, disputed_items, involved_samples,
                application_channel, status, quality_inspector, registered_by,
                submitted_at, created_at, updated_at
            ) VALUES (
                :ono, :rno, :cno, :cn, :ct, :desc, :en, :di, :isamp,
                :ac, '调查中', :qi, :a, now(), now(), now()
            )"""),
        {"ono": objection_no, "rno": body.report_no, "cno": report.get("commission_no", ""),
         "cn": body.client_name, "ct": body.contact, "desc": body.description,
         "en": body.evidence_note, "di": "、".join(disputed), "isamp": body.involved_samples,
         "ac": body.application_channel, "qi": inspector, "a": actor},
    )

    await db.execute(
        text("""INSERT INTO objection_actions (objection_no, actor, action, comment, created_at)
                VALUES (:n, :a, '登记客户异议', :c, now())"""),
        {"n": objection_no, "a": actor, "c": body.description[:200]},
    )

    # 标记报告为异议处理中
    await db.execute(
        text("UPDATE reports SET validity_status='异议处理中', updated_at=now() WHERE report_no=:r"),
        {"r": body.report_no},
    )

    await _notify(db, [inspector], "客户异议待调查",
                  f"样品管理员已登记异议 {objection_no}，关联报告 {body.report_no}，请调取追溯资料并完成责任判定。",
                  "objection", objection_no)

    return {"objection_no": objection_no, "status": "调查中", "quality_inspector": inspector}


@router.put("/{objection_no}/investigate")
async def investigate_objection(
    objection_no: str,
    body: InvestigateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """质量负责人提交调查结论"""
    actor = user["username"]
    obj = await db.execute(
        text("SELECT * FROM objections WHERE objection_no=:n"), {"n": objection_no})
    row = obj.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异议不存在")
    item = dict(zip(obj.keys(), row))

    if item.get("quality_inspector") != actor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有指定的质量负责人可提交调查")
    if item.get("status") != "调查中":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前异议不在调查阶段")

    if body.pathway not in ("是我方问题", "样品问题"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="必须选择检查路径：是我方问题 / 样品问题")
    if not body.investigation.strip() or not body.trace_conclusion.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="调查过程和结论均不能为空")

    next_status = "待客户确认重测" if body.pathway == "是我方问题" else "待异议回复"
    report_validity = "异议成立-暂停使用" if body.pathway == "是我方问题" else "有效"

    await db.execute(
        text("""UPDATE objections SET pathway=:pw, investigation=:inv, trace_conclusion=:tc,
                quality_evidence=:qe, quality_method_check=:qm, quality_equipment_check=:qeq,
                quality_environment_check=:qen, quality_operation_check=:qo,
                quality_calculation_check=:qc, impact_scope=:isc, treatment_suggestion=:ts,
                status=:st, investigated_at=now(), updated_at=now()
                WHERE objection_no=:n"""),
        {"n": objection_no, "pw": body.pathway, "inv": body.investigation,
         "tc": body.trace_conclusion, "qe": body.quality_evidence,
         "qm": body.quality_method_check, "qeq": body.quality_equipment_check,
         "qen": body.quality_environment_check, "qo": body.quality_operation_check,
         "qc": body.quality_calculation_check, "isc": body.impact_scope,
         "ts": body.treatment_suggestion, "st": next_status},
    )

    await db.execute(
        text("UPDATE reports SET validity_status=:v, updated_at=now() WHERE report_no=:r"),
        {"v": report_validity, "r": item.get("report_no")},
    )

    await db.execute(
        text("""INSERT INTO objection_actions (objection_no, actor, action, comment, created_at)
                VALUES (:n, :a, '提交调查结论', :c, now())"""),
        {"n": objection_no, "a": actor, "c": f"{body.pathway}｜{body.trace_conclusion}"},
    )

    # 通知样品管理员
    receivers = await db.execute(
        text("SELECT username FROM users WHERE role='样品管理员' AND enabled IS TRUE"))
    for r in receivers.fetchall():
        await _notify(db, [r[0]], "客户异议待处理",
                      f'异议 {objection_no} 已完成调查，判定为“{body.pathway}”。',
                      "objection", objection_no)

    return {"message": "调查结论已提交", "status": next_status, "pathway": body.pathway}


@router.put("/{objection_no}/retest-decision")
async def record_retest_decision(
    objection_no: str,
    body: RetestDecisionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """样品管理员记录客户重测决定"""
    actor = user["username"]
    if user.get("role") != "样品管理员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有样品管理员可以记录客户重测决定")

    obj = await db.execute(
        text("SELECT * FROM objections WHERE objection_no=:n"), {"n": objection_no})
    row = obj.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异议不存在")
    item = dict(zip(obj.keys(), row))
    if item.get("status") != "待客户确认重测":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前异议不在客户重测确认阶段")

    if body.decision not in ("需要重测", "不需要重测"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="客户决定选项无效")

    new_status = "待安排重测" if body.decision == "需要重测" else "待异议回复"

    await db.execute(
        text("""UPDATE objections SET customer_retest_decision=:d, retest_note=:n,
                status=:st, updated_at=now() WHERE objection_no=:ono"""),
        {"d": body.decision, "n": body.note, "st": new_status, "ono": objection_no},
    )

    await db.execute(
        text("""INSERT INTO objection_actions (objection_no, actor, action, comment, created_at)
                VALUES (:n, :a, '记录客户重测决定', :c, now())"""),
        {"n": objection_no, "a": actor, "c": f"{body.decision}｜{body.note}"},
    )

    return {"message": "客户重测决定已记录", "status": new_status, "decision": body.decision}


@router.post("/{objection_no}/dispatch-retest")
async def dispatch_retest(
    objection_no: str,
    body: DispatchRetestRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """样品管理员下发留样重测任务"""
    actor = user["username"]
    if user.get("role") != "样品管理员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有样品管理员可下发重测")

    obj = await db.execute(
        text("SELECT * FROM objections WHERE objection_no=:n"), {"n": objection_no})
    row = obj.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异议不存在")
    item = dict(zip(obj.keys(), row))
    if item.get("status") != "待安排重测" or item.get("customer_retest_decision") != "需要重测":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前异议不能下发留样重测")

    # 获取原任务
    original_report = await db.execute(
        text("SELECT task_no FROM reports WHERE report_no=:r"), {"r": item.get("report_no")})
    orig_rep = original_report.fetchone()
    if not orig_rep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="原报告任务不存在")

    orig_task = await db.execute(
        text("SELECT * FROM tasks WHERE task_no=:t"), {"t": orig_rep[0]})
    ot = orig_task.fetchone()
    if not ot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="原实验任务不存在")
    orig = dict(zip(orig_task.keys(), ot))

    # 检查可用留样
    samples = await db.execute(
        text("SELECT * FROM samples WHERE group_id=:gid"), {"gid": orig.get("group_id")})
    sample_list = [dict(zip(samples.keys(), s)) for s in samples.fetchall()]
    available = {
        s["sample_no"]: s for s in sample_list
        if s.get("status") not in ("全部消耗，记录归档", "已销毁", "已报废")
    }
    if not available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可用于重测的留样")

    sample_nos = body.selected_sample_nos if body.selected_sample_nos else list(available.keys())
    if any(sno not in available for sno in sample_nos):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="所选样品不在可用留样库中")

    # 匹配复核员和质量负责人
    reviewer = await _auto_match_user(db, "复核员", {body.assignee})
    quality_inspector = await _auto_match_user(db, "质量负责人", {body.assignee, reviewer})

    # 创建重测任务包
    pkg_count = await db.execute(
        text("SELECT COUNT(*) FROM task_packages WHERE group_no=:gn"), {"gn": orig.get("group_no")})
    pkg_seq = pkg_count.fetchone()[0] + 1
    package_no = f"{orig.get('group_no')}-P{pkg_seq:02d}"

    task_count = await db.execute(
        text("SELECT COUNT(*) FROM tasks WHERE group_no=:gn"), {"gn": orig.get("group_no")})
    task_seq = task_count.fetchone()[0] + 1
    task_no = f"{orig.get('group_no')}-T{task_seq:02d}"

    # 创建任务包
    await db.execute(
        text("""INSERT INTO task_packages (
                package_no, commission_no, group_id, group_no, assignee, reviewer, quality_inspector,
                material_name, sample_nos, experiment_codes, experiments, status, assigned_by,
                assigned_at, notified_at, created_at, updated_at
            ) VALUES (
                :pn, :cno, :gid, :gno, :a, :rv, :qi, :mn,
                :sns::jsonb, :ecs::jsonb, :exps::jsonb, '待接收', :ab, now(), now(), now(), now()
            )"""),
        {"pn": package_no, "cno": orig.get("commission_no"), "gid": orig.get("group_id"),
         "gno": orig.get("group_no"), "a": body.assignee, "rv": reviewer, "qi": quality_inspector,
         "mn": orig.get("material_name", ""),
         "sns": json.dumps(sample_nos, ensure_ascii=False),
         "ecs": json.dumps([orig.get("experiment_code")], ensure_ascii=False),
         "exps": json.dumps([orig.get("experiment")], ensure_ascii=False),
         "ab": actor},
    )

    # 创建任务
    await db.execute(
        text("""INSERT INTO tasks (
                task_no, package_no, commission_no, group_id, group_no, sample_nos,
                experiment_code, experiment, method_code, standard, material_name,
                assignee, reviewer, quality_inspector, status, created_at, updated_at
            ) VALUES (
                :tn, :pn, :cno, :gid, :gno, :sns::jsonb,
                :ec, :exp, :mc, :std, :mn, :a, :rv, :qi, '待接收', now(), now()
            )"""),
        {"tn": task_no, "pn": package_no, "cno": orig.get("commission_no"),
         "gid": orig.get("group_id"), "gno": orig.get("group_no"),
         "sns": json.dumps(sample_nos, ensure_ascii=False),
         "ec": orig.get("experiment_code"), "exp": orig.get("experiment"),
         "mc": orig.get("method_code"), "std": orig.get("standard"),
         "mn": orig.get("material_name", ""), "a": body.assignee,
         "rv": reviewer, "qi": quality_inspector},
    )

    # 更新异议
    await db.execute(
        text("""UPDATE objections SET retest_task_no=:rt, status='重测任务已下发',
                retest_note=COALESCE(retest_note,'')||:rn, updated_at=now()
                WHERE objection_no=:n"""),
        {"rt": task_no, "rn": f"；使用留样重测，任务{task_no}", "n": objection_no},
    )

    await db.execute(
        text("""INSERT INTO objection_actions (objection_no, actor, action, comment, created_at)
                VALUES (:n, :a, '下发留样重测任务', :c, now())"""),
        {"n": objection_no, "a": actor, "c": task_no},
    )

    # 更新样品状态
    for sno in sample_nos:
        await db.execute(
            text("UPDATE samples SET status='待接收重测', current_holder=:a, updated_at=now() WHERE sample_no=:sn"),
            {"sn": sno, "a": body.assignee},
        )

    await _notify(db, [body.assignee], "收到异议重测任务",
                  f"异议 {objection_no} 已从样品库派发留样，重测任务 {task_no}，请接收后按原流程检测。",
                  "task", task_no)

    return {"message": "重测任务已下发", "retest_task_no": task_no, "package_no": package_no}


@router.put("/{objection_no}/prepare-response")
async def prepare_response(
    objection_no: str,
    body: PrepareResponseRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """样品管理员生成异议回复单"""
    actor = user["username"]
    if user.get("role") != "样品管理员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有样品管理员可以生成回复")

    obj = await db.execute(
        text("SELECT * FROM objections WHERE objection_no=:n"), {"n": objection_no})
    row = obj.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异议不存在")
    item = dict(zip(obj.keys(), row))
    if item.get("status") != "待异议回复":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前异议不在待回复阶段")

    if not body.response_text.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="回复正文不能为空")

    await db.execute(
        text("""UPDATE objections SET response_text=:rt, response_method=:rm,
                status='待发送', updated_at=now() WHERE objection_no=:n"""),
        {"rt": body.response_text, "rm": body.response_method, "n": objection_no},
    )

    await db.execute(
        text("""INSERT INTO objection_actions (objection_no, actor, action, comment, created_at)
                VALUES (:n, :a, '生成异议回复单', :c, now())"""),
        {"n": objection_no, "a": actor, "c": body.response_text[:200]},
    )

    return {"message": "异议回复单已生成", "status": "待发送"}


@router.put("/{objection_no}/send")
async def send_objection(
    objection_no: str,
    body: SendResponseRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """样品管理员发送异议回复并归档"""
    actor = user["username"]
    if user.get("role") != "样品管理员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有样品管理员可以发送回复")

    obj = await db.execute(
        text("SELECT * FROM objections WHERE objection_no=:n"), {"n": objection_no})
    row = obj.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="异议不存在")
    item = dict(zip(obj.keys(), row))
    if item.get("status") != "待发送":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="异议回复尚未签发")

    await db.execute(
        text("""UPDATE objections SET status='已归档', sent_by=:a, sent_at=now(),
                archived_at=now(), response_receipt=:rc, updated_at=now()
                WHERE objection_no=:n"""),
        {"a": actor, "rc": body.note, "n": objection_no},
    )

    await db.execute(
        text("""INSERT INTO objection_actions (objection_no, actor, action, comment, created_at)
                VALUES (:n, :a, '发送回复并自动归档', :c, now())"""),
        {"n": objection_no, "a": actor, "c": body.note},
    )

    return {"message": "异议已归档", "status": "已归档"}
