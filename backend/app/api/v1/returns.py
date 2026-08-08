"""回库确认 API — 样品借出归还管理"""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/returns", tags=["回库确认"])


class ReturnConfirm(BaseModel):
    return_condition: str | None = None
    return_note: str | None = None
    confirmed_location: str | None = None


class SubmitReturnRequest(BaseModel):
    package_no: str
    sample_nos: list[str]
    detection_location: str = ""
    purpose: str = "实验检测"
    issue_note: str = ""


class SubmitLoanRequest(BaseModel):
    """借出登记（实验员从样品库取出样品时登记）"""
    package_no: str
    sample_nos: list[str]
    detection_location: str = ""
    purpose: str = "实验检测"
    issue_note: str = ""


@router.get("")
async def list_returns(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    package_no: str | None = Query(None, description="任务包编号过滤"),
    return_status: str | None = Query(None, description="归还状态过滤：未归还/已归还/已确认"),
    search: str | None = Query(None, description="搜索样品编号或借用人"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """样品借出/归还记录列表"""
    where = "WHERE 1=1"
    params: dict = {}

    if package_no:
        where += " AND pl.package_no = :pkg"
        params["pkg"] = package_no
    if return_status:
        where += " AND pl.return_status = :rs"
        params["rs"] = return_status
    if search:
        where += " AND (pl.sample_no ILIKE :s OR pl.borrower ILIKE :s)"
        params["s"] = f"%{search}%"

    result = await db.execute(
        text(f"""
            SELECT pl.id, pl.package_no, pl.sample_no, pl.borrower, pl.borrowed_at,
                   pl.purpose, pl.detection_location, pl.issue_note,
                   pl.return_condition, pl.return_note, pl.returned_by, pl.returned_at,
                   pl.return_status, pl.confirmed_by, pl.confirmed_at, pl.confirmed_location,
                   s.sample_name, s.material_name
            FROM package_loans pl
            LEFT JOIN samples s ON pl.sample_no = s.sample_no
            {where}
            ORDER BY pl.borrowed_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    )
    rows = result.fetchall()
    return [dict(zip(result.keys(), r)) for r in rows]


@router.put("/{loan_id}/confirm")
async def confirm_return(
    loan_id: int,
    body: ReturnConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """确认样品回库（样品管理员操作）"""
    # 检查记录存在
    result = await db.execute(
        text("SELECT id, return_status FROM package_loans WHERE id=:id"),
        {"id": loan_id},
    )
    loan = result.fetchone()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="借出记录不存在")
    if loan[1] == "已确认":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该记录已确认回库")

    now = text("now()")
    await db.execute(
        text("""
            UPDATE package_loans
            SET return_condition = COALESCE(:cond, return_condition),
                return_note = COALESCE(:note, return_note),
                return_status = '已确认',
                confirmed_by = :user,
                confirmed_at = :now,
                confirmed_location = COALESCE(:loc, confirmed_location)
            WHERE id = :id
        """),
        {
            "id": loan_id,
            "cond": body.return_condition,
            "note": body.return_note,
            "loc": body.confirmed_location,
            "user": user["username"],
            "now": now,
        },
    )

    # 记录审计日志
    await db.execute(
        text("""
            INSERT INTO audit_logs (entity_type, entity_id, actor, actor_name, actor_role, action, created_at)
            VALUES ('package_loan', :eid, :actor, :name, :role, 'confirm_return', now())
        """),
        {
            "eid": str(loan_id),
            "actor": user["username"],
            "name": user.get("display_name", ""),
            "role": user.get("role", ""),
        },
    )

    return {"message": "回库已确认", "loan_id": loan_id}


@router.post("/loan", status_code=201)
async def submit_loan(
    body: SubmitLoanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """实验员登记样品借出"""
    actor = user["username"]
    if user.get("role") != "实验员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有实验员可以登记借出")

    # 验证任务包
    pkg = await db.execute(
        text("SELECT package_no, commission_no, assignee FROM task_packages WHERE package_no=:pn"),
        {"pn": body.package_no},
    )
    pkg_row = pkg.fetchone()
    if not pkg_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务包不存在")
    pkg_data = dict(zip(pkg.keys(), pkg_row))
    if pkg_data.get("assignee") != actor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能借出自己负责的任务包样品")

    if not body.sample_nos:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="至少选择一个样品")

    inserted = []
    for sno in body.sample_nos:
        # 验证样品属于该委托
        s = await db.execute(
            text("SELECT sample_no, status FROM samples WHERE sample_no=:sn"),
            {"sn": sno},
        )
        s_row = s.fetchone()
        if not s_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"样品 {sno} 不存在")
        s_data = dict(zip(s.keys(), s_row))
        if s_data.get("status") != "已入库":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"样品 {sno} 状态为'{s_data.get('status')}'，不可借出")

        await db.execute(
            text("""INSERT INTO package_loans (
                    package_no, sample_no, borrower, borrowed_at, purpose,
                    detection_location, issue_note, return_status, created_at, updated_at
                ) VALUES (
                    :pn, :sn, :b, now(), :p, :dl, :inote, '未归还', now(), now()
                )"""),
            {"pn": body.package_no, "sn": sno, "b": actor,
             "p": body.purpose, "dl": body.detection_location, "inote": body.issue_note},
        )

        # 更新样品状态
        await db.execute(
            text("UPDATE samples SET status='借出中', current_holder=:a, updated_at=now() WHERE sample_no=:sn"),
            {"sn": sno, "a": actor},
        )
        inserted.append(sno)

    return {"message": f"已登记 {len(inserted)} 个样品借出", "loan_count": len(inserted),
            "package_no": body.package_no, "sample_nos": inserted}


@router.post("/submit", status_code=201)
async def submit_return(
    body: SubmitReturnRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """实验员提交样品归还清单"""
    actor = user["username"]
    if user.get("role") != "实验员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有实验员可以提交归还")

    if not body.sample_nos:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="至少选择一个样品")

    updated = 0
    for sno in body.sample_nos:
        res = await db.execute(
            text("""SELECT id, return_status FROM package_loans
                    WHERE package_no=:pn AND sample_no=:sn AND borrower=:b"""),
            {"pn": body.package_no, "sn": sno, "b": actor},
        )
        loan = res.fetchone()
        if not loan:
            continue
        if dict(zip(res.keys(), loan)).get("return_status") != "未归还":
            continue

        await db.execute(
            text("""UPDATE package_loans SET return_status='已归还',
                    returned_by=:b, returned_at=now(), updated_at=now()
                    WHERE id=:id"""),
            {"id": loan[0], "b": actor},
        )
        updated += 1

    if updated == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可归还的借出记录")

    # 通知样品管理员
    admins = await db.execute(
        text("SELECT username FROM users WHERE role='样品管理员' AND enabled IS TRUE"))
    for r in admins.fetchall():
        await db.execute(
            text("""INSERT INTO notifications (recipient, title, message, entity_type, entity_id, created_at)
                    VALUES (:r, '样品待确认回库', :b, 'package_loan', :pn, now())"""),
            {"r": r[0], "b": f"任务包{body.package_no}中{updated}个样品已归还，请确认回库", "pn": body.package_no},
        )

    return {"message": f"已提交 {updated} 个样品归还", "return_count": updated}


@router.get("/pending")
async def list_pending_returns(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """样品管理员查看待确认的归还记录"""
    result = await db.execute(
        text("""
            SELECT pl.*, s.sample_name, s.material_name
            FROM package_loans pl
            LEFT JOIN samples s ON pl.sample_no = s.sample_no
            WHERE pl.return_status = '已归还'
            ORDER BY pl.returned_at DESC
            LIMIT 200
        """)
    )
    return [dict(zip(result.keys(), r)) for r in result.fetchall()]


@router.get("/stats")
async def return_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """回库统计"""
    result = await db.execute(
        text("""
            SELECT return_status, COUNT(*) as cnt
            FROM package_loans
            GROUP BY return_status
        """)
    )
    stats = {r[0]: r[1] for r in result.fetchall()}
    return {
        "total": sum(stats.values()),
        "unreturned": stats.get("未归还", 0),
        "returned": stats.get("已归还", 0),
        "confirmed": stats.get("已确认", 0),
    }
