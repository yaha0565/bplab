"""危废处理 API"""
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

router = APIRouter(prefix="/hazardous-waste", tags=["危废处理"])


class CreateWasteRequest(BaseModel):
    task_nos: list[str]  # 支持多任务关联
    waste_type: str = "实验废液"
    waste_name: str
    quantity: float
    unit: str = "mL"
    hazard_category: str = ""
    disposal_method: str
    container_no: str = ""
    occurred_at: str | None = None
    note: str = ""


def _next_waste_no(now: datetime = None) -> str:
    dt = now or china_now()
    return f"D{dt.strftime('%Y%m%d')}"


@router.get("")
async def list_waste(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    task_no: str | None = Query(None),
):
    """危废记录列表（实验员只看自己的）"""
    role = user.get("role", "")
    username = user.get("username", "")

    where = "WHERE 1=1"
    params: dict = {}
    if role == "实验员":
        where += " AND handler=:u"
        params["u"] = username
    if task_no:
        where += " AND task_no=:tn"
        params["tn"] = task_no

    result = await db.execute(
        text(f"SELECT * FROM hazardous_waste_records {where} ORDER BY occurred_at DESC"),
        params,
    )
    return [dict(zip(result.keys(), r)) for r in result.fetchall()]


@router.post("", status_code=201)
async def create_waste(
    body: CreateWasteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """实验员登记危废处置"""
    actor = user["username"]
    if user.get("role") != "实验员":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有实验员可以登记危废处置")

    task_nos = list(dict.fromkeys(str(x).strip() for x in body.task_nos if str(x).strip()))
    if not task_nos:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="至少选择一个产生危废的实验任务")

    # 验证所有任务属于同一委托
    commissions = set()
    task_data = None
    for tn in task_nos:
        t = await db.execute(text("SELECT * FROM tasks WHERE task_no=:tn"), {"tn": tn})
        row = t.fetchone()
        if not row or dict(zip(t.keys(), row)).get("assignee") != actor:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"只能关联本人负责的实验任务: {tn}")
        item = dict(zip(t.keys(), row))
        commissions.add(item.get("commission_no"))
        if task_data is None:
            task_data = item

    if len(commissions) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="同一条危废记录只能关联同一委托下的任务")

    if not body.waste_name.strip() or not body.disposal_method.strip() or body.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="危废名称、正数数量和处置方式均为必填项")

    # 生成编号
    prefix = _next_waste_no()
    seq_result = await db.execute(
        text("SELECT disposal_no FROM hazardous_waste_records WHERE disposal_no LIKE :pat ORDER BY disposal_no DESC LIMIT 1"),
        {"pat": f"{prefix}%"},
    )
    last = seq_result.fetchone()
    seq = int(last[0][-3:]) + 1 if last else 1
    disposal_no = f"{prefix}{seq:03d}"

    await db.execute(
        text("""INSERT INTO hazardous_waste_records (
                disposal_no, commission_no, task_no, task_nos, waste_type, waste_name,
                quantity, unit, hazard_category, disposal_method, container_no, handler,
                occurred_at, status, note, created_by, created_at, updated_at
            ) VALUES (
                :dn, :cno, :tn, :tns::jsonb, :wt, :wn, :q, :u, :hc, :dm, :cn, :h,
                :oa, '已登记', :note, :a, now(), now()
            )"""),
        {"dn": disposal_no, "cno": task_data.get("commission_no"), "tn": task_data.get("task_no"),
         "tns": json.dumps(task_nos, ensure_ascii=False), "wt": body.waste_type,
         "wn": body.waste_name, "q": body.quantity, "u": body.unit,
         "hc": body.hazard_category, "dm": body.disposal_method,
         "cn": body.container_no, "h": actor,
         "oa": body.occurred_at or china_now().isoformat(), "note": body.note, "a": actor},
    )

    return {"disposal_no": disposal_no, "status": "已登记"}
