"""报告 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/reports", tags=["报告"])


class ReportBrief(BaseModel):
    report_no: str
    commission_no: str
    status: str
    tester: str | None
    verifier: str | None
    quality_inspector: str | None
    publish_date: str | None
    created_at: str | None


# ── 生成报告 ──

class GenerateReportRequest(BaseModel):
    task_no: str


@router.post("")
async def generate_report(
    body: GenerateReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("质量负责人", "复核员"))],
):
    """为已完成的任务生成检验报告"""
    # 验证任务已完成
    task_result = await db.execute(
        text("SELECT commission_no, experiment FROM tasks WHERE task_no=:t AND status='已完成'"),
        {"t": body.task_no},
    )
    task = task_result.fetchone()
    if not task:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务未完成，无法生成报告")

    # 检查是否已有报告
    existing = await db.execute(
        text("SELECT report_no FROM reports WHERE task_no=:t"),
        {"t": body.task_no},
    )
    if existing.fetchone():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该任务已有报告")

    # 检查是否有已锁定的记录
    record_check = await db.execute(
        text("SELECT 1 FROM records WHERE task_no=:t AND status='已锁定'"),
        {"t": body.task_no},
    )
    if not record_check.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="记录未通过复核，无法生成报告")

    # 生成报告编号: R + YYYYMMDD + 3位序号 - T{NN}
    from datetime import date
    today_str = date.today().strftime("%Y%m%d")
    task_seq = body.task_no.split("-T")[-1] if "-T" in body.task_no else "01"
    count_result = await db.execute(
        text("SELECT MAX(report_no) FROM reports WHERE report_no LIKE :pattern"),
        {"pattern": f"R{today_str}%"},
    )
    max_no = count_result.fetchone()[0]
    if max_no:
        seq = int(max_no[1:9]) + 1 if len(max_no) > 9 else 1
    else:
        seq = 1
    report_no = f"R{today_str}{seq:03d}-T{task_seq}"

    # 查任务信息
    task_detail = await db.execute(
        text("SELECT t.commission_no, t.experiment, t.assignee, tp.reviewer FROM tasks t LEFT JOIN task_packages tp ON t.package_no=tp.package_no WHERE t.task_no=:t"),
        {"t": body.task_no},
    )
    detail = task_detail.fetchone()

    await db.execute(
        text("""
            INSERT INTO reports (report_no, task_no, commission_no, experiment, tester, verifier,
              status, created_at, updated_at)
            VALUES (:rn, :tn, :cn, :ex, :tr, :vf, '草稿', now(), now())
        """),
        {
            "rn": report_no, "tn": body.task_no,
            "cn": detail[0] if detail else "", "ex": detail[1] if detail else "",
            "tr": detail[2] if detail else "", "vf": detail[3] if detail else "",
        },
    )

    return {"report_no": report_no, "status": "草稿", "message": "报告已生成"}


# ── 质量审核 ──

class ReviewReportRequest(BaseModel):
    decision: str = Field(..., pattern=r"^(通过|退回)$")
    comment: str = ""


@router.post("/{report_no}/quality-review")
async def quality_review_report(
    report_no: str,
    body: ReviewReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("质量负责人"))],
):
    """质量负责人审核报告"""
    rep = await db.execute(
        text("SELECT status FROM reports WHERE report_no=:r"),
        {"r": report_no},
    )
    rep_row = rep.fetchone()
    if not rep_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    if rep_row[0] not in ("草稿", "已退回"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"报告状态为'{rep_row[0]}'，无法审核")

    new_status = "待签发" if body.decision == "通过" else "已退回"
    await db.execute(
        text("UPDATE reports SET status=:st, quality_inspector=:qi, updated_at=now() WHERE report_no=:r"),
        {"st": new_status, "qi": user["username"], "r": report_no},
    )

    # 记录操作
    await db.execute(
        text("INSERT INTO report_actions (report_no, actor, action, comment, created_at) VALUES (:r, :a, :ac, :c, now())"),
        {"r": report_no, "a": user["username"], "ac": f"质量审核-{body.decision}", "c": body.comment},
    )

    return {"message": f"质量审核{body.decision}", "status": new_status}


# ── 批准签发 ──

@router.post("/{report_no}/approve")
async def approve_report(
    report_no: str,
    body: ReviewReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("质量负责人", "管理员"))],
):
    """批准并签发报告"""
    rep = await db.execute(
        text("SELECT status FROM reports WHERE report_no=:r"),
        {"r": report_no},
    )
    rep_row = rep.fetchone()
    if not rep_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    if rep_row[0] != "待签发":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"报告状态为'{rep_row[0]}'，无法签发")

    await db.execute(
        text("UPDATE reports SET status='已发布', approver=:ap, publish_date=now(), updated_at=now() WHERE report_no=:r"),
        {"ap": user["username"], "r": report_no},
    )

    await db.execute(
        text("INSERT INTO report_actions (report_no, actor, action, comment, created_at) VALUES (:r, :a, :ac, :c, now())"),
        {"r": report_no, "a": user["username"], "ac": "批准签发", "c": body.comment},
    )

    return {"message": "报告已签发", "status": "已发布"}


@router.get("", response_model=list[ReportBrief])
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
):
    """报告列表（按角色过滤）"""
    role = user["role"]
    username = user["username"]

    params: dict = {}
    if role == "质量负责人":
        where = "WHERE quality_inspector=:username OR status IN ('待签发','已签发')"
        params["username"] = username
    elif role == "复核员":
        where = "WHERE verifier=:username"
        params["username"] = username
    elif role == "实验员":
        where = "WHERE tester=:username"
        params["username"] = username
    else:
        where = "WHERE 1=1"

    if status_filter:
        where += " AND status=:status_filter"
        params["status_filter"] = status_filter

    result = await db.execute(
        text(f"SELECT report_no, commission_no, status, tester, verifier, quality_inspector, publish_date, created_at FROM reports {where} ORDER BY created_at DESC LIMIT :limit"),
        {**params, "limit": limit},
    )
    return [
        ReportBrief(report_no=r[0], commission_no=r[1], status=r[2], tester=r[3],
                    verifier=r[4], quality_inspector=r[5],
                    publish_date=str(r[6]) if r[6] else None,
                    created_at=str(r[7]) if r[7] else None)
        for r in result.fetchall()
    ]


@router.get("/{report_no}")
async def get_report(
    report_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """报告详情"""
    result = await db.execute(
        text("SELECT * FROM reports WHERE report_no=:r"), {"r": report_no}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    report = dict(zip(result.keys(), row))

    # 操作历史
    actions_result = await db.execute(
        text("SELECT actor, action, comment, created_at FROM report_actions WHERE report_no=:r ORDER BY created_at"),
        {"r": report_no},
    )
    report["actions"] = [dict(zip(actions_result.keys(), r)) for r in actions_result.fetchall()]

    return report


# ── 报告发放 ──

class DeliverReportRequest(BaseModel):
    delivery_method: str  # 自取/邮寄/电子邮件/其他
    recipient: str
    recipient_contact: str = ""
    tracking_no: str = ""
    note: str = ""


@router.post("/{report_no}/delivery")
async def deliver_report(
    report_no: str,
    body: DeliverReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("样品管理员"))],
):
    """登记报告发放"""
    rep = await db.execute(
        text("SELECT status, commission_no FROM reports WHERE report_no=:r"),
        {"r": report_no},
    )
    rep_row = rep.fetchone()
    if not rep_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    if rep_row[0] != "已发布":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"报告状态为'{rep_row[0]}'，不能发放")

    if not body.delivery_method.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="发放方式不能为空")
    if not body.recipient.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="接收人不能为空")

    await db.execute(
        text("""INSERT INTO report_deliveries (
                report_no, commission_no, delivery_method, recipient, recipient_contact,
                tracking_no, note, delivered_by, delivered_at, created_at
            ) VALUES (
                :rn, :cn, :dm, :rc, :rct, :tn, :n, :db, now(), now()
            )"""),
        {"rn": report_no, "cn": rep_row[1], "dm": body.delivery_method,
         "rc": body.recipient, "rct": body.recipient_contact,
         "tn": body.tracking_no, "n": body.note, "db": user["username"]},
    )

    await db.execute(
        text("INSERT INTO report_actions (report_no, actor, action, comment, created_at) VALUES (:r, :a, '报告发放', :c, now())"),
        {"r": report_no, "a": user["username"], "c": f"方式：{body.delivery_method}｜接收人：{body.recipient}"},
    )

    return {"message": "报告发放已登记", "report_no": report_no, "recipient": body.recipient}


@router.get("/{report_no}/deliveries")
async def list_deliveries(
    report_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """报告发放记录"""
    result = await db.execute(
        text("SELECT * FROM report_deliveries WHERE report_no=:r ORDER BY delivered_at DESC"),
        {"r": report_no},
    )
    return [dict(zip(result.keys(), r)) for r in result.fetchall()]


# ── 报告撤回 ──

@router.post("/{report_no}/revoke")
async def revoke_report(
    report_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("质量负责人", "管理员"))],
):
    """撤回已签发的报告（质量负责人/管理员）"""
    rep = await db.execute(
        text("SELECT status FROM reports WHERE report_no=:r"), {"r": report_no})
    row = rep.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    if row[0] != "已发布":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"报告状态为'{row[0]}'，只能撤回已签发的报告")

    await db.execute(
        text("UPDATE reports SET status='已撤回', updated_at=now() WHERE report_no=:r"), {"r": report_no})
    await db.execute(
        text("INSERT INTO report_actions (report_no, actor, action, comment, created_at) VALUES (:r, :a, '撤回报告', now())"),
        {"r": report_no, "a": user["username"]},
    )
    return {"message": "报告已撤回", "report_no": report_no, "status": "已撤回"}
