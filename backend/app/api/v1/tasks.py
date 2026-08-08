"""任务包 + 实验任务 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/tasks", tags=["任务"])


class TaskPackageBrief(BaseModel):
    package_no: str
    commission_no: str
    group_no: str
    assignee: str
    reviewer: str
    assigned_by: str | None
    material_name: str | None
    experiments: str | None
    status: str
    assigned_at: str | None


class TaskBrief(BaseModel):
    task_no: str
    package_no: str
    experiment: str | None
    method_code: str | None
    status: str
    detection_location: str | None
    experiment_started_at: str | None
    experiment_ended_at: str | None


# ── 创建任务包 ──

class CreatePackageRequest(BaseModel):
    group_id: int
    experiment_codes: list[str]
    assignee: str
    reviewer: str
    detection_locations: dict[str, str] = {}  # experiment_code → location


@router.post("/packages")
async def create_package(
    body: CreatePackageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """创建任务包并绑定委托、分配实验员"""
    # 查询样品组信息
    group_result = await db.execute(
        text("SELECT group_no, commission_no, material_name FROM sample_groups WHERE id=:i AND is_void=FALSE"),
        {"i": body.group_id},
    )
    group = group_result.fetchone()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="样品组不存在")

    group_no = group[0]
    commission_no = group[1]
    material_name = group[2]

    # 验证委托存在且有效
    comm_result = await db.execute(
        text("SELECT commission_no, status FROM commissions WHERE commission_no=:c"),
        {"c": commission_no},
    )
    comm = comm_result.fetchone()
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"委托 {commission_no} 不存在")
    if comm[1] == "已作废":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"委托 {commission_no} 已作废，无法创建任务包")

    # 查询实验方法
    experiments_str = ", ".join(body.experiment_codes)
    method_names = []
    for code in body.experiment_codes:
        m = await db.execute(
            text("SELECT experiment_name, method_code FROM experiment_methods WHERE experiment_code=:c"),
            {"c": code},
        )
        row = m.fetchone()
        if row:
            method_names.append(row[0])

    experiments_label = ", ".join(method_names) if method_names else experiments_str

    # 生成任务包编号: BAG-BP{group_no}-P{seq}
    count_result = await db.execute(
        text("SELECT COUNT(*) FROM task_packages WHERE group_no=:g"),
        {"g": group_no},
    )
    pkg_seq = count_result.fetchone()[0] + 1
    package_no = f"BAG-{group_no}-P{pkg_seq:02d}"

    # 插入任务包（绑定委托，记录分配人）
    await db.execute(
        text("""
            INSERT INTO task_packages (package_no, commission_no, group_id, group_no, assignee, reviewer,
              assigned_by, material_name, experiment_codes, experiments, status, assigned_at, created_at, updated_at)
            VALUES (:pn, :cn, :gid, :gn, :a, :rv, :ab, :mn, :ec, :ex, '待接收', now(), now(), now())
        """),
        {
            "pn": package_no, "cn": commission_no, "gid": body.group_id, "gn": group_no,
            "a": body.assignee, "rv": body.reviewer, "ab": user["username"],
            "mn": material_name, "ec": experiments_str, "ex": experiments_label,
        },
    )

    # 为每个实验方法创建任务
    tasks_created = []
    for seq, code in enumerate(body.experiment_codes, 1):
        task_no = f"{package_no}-T{seq:02d}"
        m = await db.execute(
            text("SELECT experiment_name, method_code, kind FROM experiment_methods WHERE experiment_code=:c"),
            {"c": code},
        )
        method = m.fetchone()
        exp_name = method[0] if method else code
        method_code = method[1] if method else None

        location = body.detection_locations.get(code, "性能检测室")

        await db.execute(
            text("""
                INSERT INTO tasks (task_no, package_no, commission_no, group_id, group_no, experiment,
                  method_code, experiment_code, assignee, status, detection_location, created_at, updated_at)
                VALUES (:tn, :pn, :cn, :gid, :gn, :ex, :mc, :ec, :a, '待接收', :dl, now(), now())
            """),
            {
                "tn": task_no, "pn": package_no, "cn": commission_no, "gid": body.group_id,
                "gn": group_no, "ex": exp_name, "mc": method_code, "ec": code, "a": body.assignee,
                "dl": location,
            },
        )
        tasks_created.append({
            "task_no": task_no,
            "experiment": exp_name,
            "method_code": method_code,
        })

    return {
        "package_no": package_no,
        "commission_no": commission_no,
        "group_no": group_no,
        "status": "待接收",
        "assigned_by": user["username"],
        "tasks": tasks_created,
    }


# ── 接收任务包 ──

class AcceptPackageRequest(BaseModel):
    acceptance_note: str = ""
    detection_locations: dict[str, str] = {}
    sample_condition: str = "完好"


@router.post("/packages/{package_no}/accept")
async def accept_package(
    package_no: str,
    body: AcceptPackageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("实验员"))],
):
    """实验员接收任务包"""
    pkg = await db.execute(
        text("SELECT status, assignee FROM task_packages WHERE package_no=:p"),
        {"p": package_no},
    )
    pkg_row = pkg.fetchone()
    if not pkg_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务包不存在")
    if pkg_row[0] != "待接收":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"任务包状态为'{pkg_row[0]}'，无法接收")
    if pkg_row[1] != user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能接收分配给自己的任务包")

    await db.execute(
        text("UPDATE task_packages SET status='检测中', updated_at=now() WHERE package_no=:p"),
        {"p": package_no},
    )

    # 更新各任务的检测地点和状态
    for task_no, location in body.detection_locations.items():
        await db.execute(
            text("UPDATE tasks SET status='检测中', detection_location=:dl, updated_at=now() WHERE task_no=:t AND package_no=:p"),
            {"dl": location, "t": task_no, "p": package_no},
        )

    return {"message": "任务包已接收", "status": "检测中"}


# ── 标记实验时间 ──

class MarkTimeRequest(BaseModel):
    action: str = Field(..., pattern=r"^(开始|结束)$")


@router.put("/{task_no}/time")
async def mark_task_time(
    task_no: str,
    body: MarkTimeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("实验员"))],
):
    """标记实验开始/结束时间"""
    task_result = await db.execute(
        text("SELECT assignee, status FROM tasks WHERE task_no=:t"),
        {"t": task_no},
    )
    task_row = task_result.fetchone()
    if not task_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task_row[0] != user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能操作自己的任务")

    if body.action == "开始":
        await db.execute(
            text("UPDATE tasks SET experiment_started_at=now(), status='检测中', updated_at=now() WHERE task_no=:t"),
            {"t": task_no},
        )
    else:
        await db.execute(
            text("UPDATE tasks SET experiment_ended_at=now(), updated_at=now() WHERE task_no=:t"),
            {"t": task_no},
        )

    return {"message": f"已标记实验{body.action}时间"}


# ── 任务包 ──

@router.get("/packages", response_model=list[TaskPackageBrief])
async def list_packages(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
):
    """任务包列表 — 实验员/复核员只看自己的；管理员/样品管理员看全部"""
    role = user["role"]
    username = user["username"]

    where_clauses = []
    params: dict = {}

    if role == "实验员":
        where_clauses.append("assignee=:username")
        params["username"] = username
    elif role == "复核员":
        where_clauses.append("reviewer=:username")
        params["username"] = username
    # 管理员、样品管理员、质量负责人 — 不添加人员限制，看全部

    if status_filter:
        where_clauses.append("status=:status_filter")
        params["status_filter"] = status_filter

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    result = await db.execute(
        text(f"SELECT package_no, commission_no, group_no, assignee, reviewer, assigned_by, material_name, experiments, status, assigned_at FROM task_packages {where} ORDER BY created_at DESC LIMIT :limit"),
        {**params, "limit": limit},
    )
    return [
        TaskPackageBrief(package_no=r[0], commission_no=r[1], group_no=r[2], assignee=r[3],
                          reviewer=r[4], assigned_by=r[5], material_name=r[6], experiments=r[7],
                          status=r[8], assigned_at=str(r[9]) if r[9] else None)
        for r in result.fetchall()
    ]


@router.get("/packages/{package_no}")
async def get_package(
    package_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """任务包详情 + 包含的实验任务"""
    result = await db.execute(
        text("SELECT * FROM task_packages WHERE package_no=:p"), {"p": package_no}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务包不存在")
    pkg = dict(zip(result.keys(), row))

    tasks_result = await db.execute(
        text("SELECT task_no, experiment, method_code, status, detection_location, experiment_started_at, experiment_ended_at FROM tasks WHERE package_no=:p ORDER BY task_no"),
        {"p": package_no},
    )
    tasks = [dict(zip(tasks_result.keys(), r)) for r in tasks_result.fetchall()]

    return {"package": pkg, "tasks": tasks}


# ── 实验任务 ──

@router.get("/my", response_model=list[TaskBrief])
async def list_my_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
):
    """我的实验任务列表"""
    params: dict = {"assignee": user["username"]}
    where = "WHERE assignee=:assignee"
    if status_filter:
        where += " AND status=:status"
        params["status"] = status_filter

    result = await db.execute(
        text(f"SELECT task_no, package_no, experiment, method_code, status, detection_location, experiment_started_at, experiment_ended_at FROM tasks {where} ORDER BY created_at DESC LIMIT :limit"),
        {**params, "limit": limit},
    )
    return [
        TaskBrief(task_no=r[0], package_no=r[1], experiment=r[2], method_code=r[3],
                  status=r[4], detection_location=r[5],
                  experiment_started_at=str(r[6]) if r[6] else None,
                  experiment_ended_at=str(r[7]) if r[7] else None)
        for r in result.fetchall()
    ]


@router.get("/{task_no}")
async def get_task(
    task_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """实验任务详情（含原始记录和附件）"""
    result = await db.execute(
        text("SELECT * FROM tasks WHERE task_no=:t"), {"t": task_no}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    task = dict(zip(result.keys(), row))

    # 原始记录
    records_result = await db.execute(
        text("SELECT record_no, version, status, owner, created_at FROM records WHERE task_no=:t ORDER BY version DESC"),
        {"t": task_no},
    )
    records = [dict(zip(records_result.keys(), r)) for r in records_result.fetchall()]

    # 附件
    att_result = await db.execute(
        text("SELECT attachment_id, attachment_type, original_name, checkpoint_code, checkpoint_label, captured_at, uploader FROM attachments WHERE task_no=:t AND evidence_status='有效' ORDER BY created_at DESC"),
        {"t": task_no},
    )
    attachments = [dict(zip(att_result.keys(), r)) for r in att_result.fetchall()]

    return {"task": task, "records": records, "attachments": attachments}
