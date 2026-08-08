"""原始记录 API"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/records", tags=["原始记录"])


class RecordBrief(BaseModel):
    record_no: str
    task_no: str
    version: int
    experiment: str | None
    status: str
    owner: str | None
    created_at: str | None


# ── 保存原始记录 ──

class SaveRecordRequest(BaseModel):
    task_no: str
    business_record: dict[str, Any] = {}
    report_summary: str = ""
    report_conclusion: str = ""
    tester_self_check: bool = False
    submit_for_review: bool = False


@router.post("")
async def save_record(
    body: SaveRecordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("实验员"))],
):
    """保存/提交原始记录"""
    # 验证任务存在且属于当前用户
    task_result = await db.execute(
        text("SELECT experiment, experiment_code, assignee FROM tasks WHERE task_no=:t"),
        {"t": body.task_no},
    )
    task = task_result.fetchone()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task[2] != user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能提交自己的实验记录")

    # 确定记录编号 = 任务编号
    record_no = body.task_no

    # 查当前版本号
    ver_result = await db.execute(
        text("SELECT COALESCE(MAX(version), 0) FROM records WHERE record_no=:r"),
        {"r": record_no},
    )
    version = ver_result.fetchone()[0] + 1

    new_status = "待复核" if body.submit_for_review else "草稿"

    import json
    payload_json = json.dumps(body.business_record, ensure_ascii=False, default=str)

    await db.execute(
        text("""
            INSERT INTO records (record_no, task_no, version, experiment, owner, status,
              payload, report_summary, report_conclusion, tester_self_check, created_at, updated_at)
            VALUES (:rn, :tn, :v, :ex, :ow, :st, :pl::jsonb, :rs, :rc, :tsc, now(), now())
        """),
        {
            "rn": record_no, "tn": body.task_no, "v": version,
            "ex": task[0], "ow": user["username"], "st": new_status,
            "pl": payload_json, "rs": body.report_summary,
            "rc": body.report_conclusion, "tsc": body.tester_self_check,
        },
    )

    # 如果提交复核，更新任务状态
    if body.submit_for_review:
        await db.execute(
            text("UPDATE tasks SET status='待复核', updated_at=now() WHERE task_no=:t"),
            {"t": body.task_no},
        )

    return {
        "record_no": record_no,
        "version": version,
        "status": new_status,
        "message": "记录已提交复核" if body.submit_for_review else "记录已保存",
    }


# ── 复核记录 ──

class ReviewRecordRequest(BaseModel):
    decision: str = Field(..., pattern=r"^(通过|退回)$")
    comment: str = ""


@router.post("/{record_no}/review")
async def review_record(
    record_no: str,
    body: ReviewRecordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("复核员"))],
):
    """复核原始记录"""
    # 获取最新版本
    rec_result = await db.execute(
        text("SELECT task_no, version, status FROM records WHERE record_no=:r ORDER BY version DESC LIMIT 1"),
        {"r": record_no},
    )
    record = rec_result.fetchone()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    if record[2] != "待复核":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"记录状态为'{record[2]}'，无法复核")

    task_no = record[0]
    version = record[1]

    # 验证复核员权限
    task_check = await db.execute(
        text("SELECT reviewer FROM tasks WHERE task_no=:t"),
        {"t": task_no},
    )
    task_row = task_check.fetchone()
    if not task_row or task_row[0] != user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能复核分配给自己的任务")

    # 插入复核记录
    await db.execute(
        text("""
            INSERT INTO reviews (record_no, version, reviewer, decision, comment, reviewed_at)
            VALUES (:rn, :v, :rv, :d, :c, now())
        """),
        {"rn": record_no, "v": version, "rv": user["username"],
         "d": body.decision, "c": body.comment},
    )

    if body.decision == "通过":
        new_status = "已锁定"
        # 更新记录状态
        await db.execute(
            text("UPDATE records SET status='已锁定', reviewer_signed_at=now(), updated_at=now() WHERE record_no=:r AND version=:v"),
            {"r": record_no, "v": version},
        )
        # 更新任务状态
        await db.execute(
            text("UPDATE tasks SET status='已完成', updated_at=now() WHERE task_no=:t"),
            {"t": task_no},
        )
    else:
        new_status = "草稿"
        await db.execute(
            text("UPDATE records SET status='草稿', updated_at=now() WHERE record_no=:r AND version=:v"),
            {"r": record_no, "v": version},
        )
        await db.execute(
            text("UPDATE tasks SET status='检测中', updated_at=now() WHERE task_no=:t"),
            {"t": task_no},
        )

    return {"message": f"复核{body.decision}", "status": new_status}


@router.get("/pending-review", response_model=list[RecordBrief])
async def pending_reviews(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(50, le=200),
):
    """待复核的记录"""
    result = await db.execute(
        text("""
            SELECT r.record_no, r.task_no, r.version, r.experiment, r.status, r.owner, r.created_at
            FROM records r
            JOIN tasks t ON t.task_no = r.task_no
            WHERE t.reviewer = :reviewer AND r.status = '待复核'
            ORDER BY r.created_at DESC LIMIT :limit
        """),
        {"reviewer": user["username"], "limit": limit},
    )
    return [
        RecordBrief(record_no=r[0], task_no=r[1], version=r[2], experiment=r[3],
                    status=r[4], owner=r[5],
                    created_at=str(r[6]) if r[6] else None)
        for r in result.fetchall()
    ]


@router.get("/{record_no}/versions")
async def record_versions(
    record_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """某记录的所有版本"""
    result = await db.execute(
        text("SELECT id, record_no, task_no, version, experiment, owner, status, template_version, sop_version, change_reason, tester_signed_at, reviewer_signed_at, quality_signed_at, created_at FROM records WHERE record_no=:r ORDER BY version DESC"),
        {"r": record_no},
    )
    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return [dict(zip(result.keys(), r)) for r in rows]


@router.get("/{record_no}/v{version}")
async def get_record(
    record_no: str,
    version: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """获取某版本的记录详情（含 payload）"""
    result = await db.execute(
        text("SELECT * FROM records WHERE record_no=:r AND version=:v"),
        {"r": record_no, "v": version},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    record = dict(zip(result.keys(), row))

    # 审核历史
    reviews_result = await db.execute(
        text("SELECT reviewer, decision, comment, reviewed_at FROM reviews WHERE record_no=:r AND version=:v ORDER BY reviewed_at"),
        {"r": record_no, "v": version},
    )
    record["reviews"] = [dict(zip(reviews_result.keys(), r)) for r in reviews_result.fetchall()]

    return record
