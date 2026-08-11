"""首页看板 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db

router = APIRouter(prefix="/dashboard", tags=["看板"])


class DashboardCounts(BaseModel):
    pending_packages: int = 0       # 待接收任务包
    active_tasks: int = 0           # 检测中任务
    pending_reviews: int = 0        # 待复核记录
    pending_reports: int = 0        # 待签发报告
    total_commissions: int = 0      # 委托总数
    total_samples: int = 0          # 样品总数
    my_packages: int = 0            # 我的任务包
    completed_tasks: int = 0        # 已完成任务
    returned_tasks: int = 0         # 退回修改任务（实验员）
    review_pending_tasks: int = 0   # 待复核任务（实验员）


@router.get("/counts", response_model=DashboardCounts)
async def dashboard_counts(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """首页统计数据（按角色返回相关统计）"""
    role = user["role"]
    username = user["username"]
    counts = DashboardCounts()

    # ── 实验员 ──
    if role == "实验员":
        # 待接收任务包
        r = await db.execute(
            text("SELECT COUNT(*) FROM task_packages WHERE assignee=:u AND status='待接收'"),
            {"u": username})
        counts.pending_packages = r.fetchone()[0]
        # 检测中任务
        r = await db.execute(
            text("SELECT COUNT(*) FROM tasks WHERE assignee=:u AND status='检测中'"),
            {"u": username})
        counts.active_tasks = r.fetchone()[0]
        # 我的任务包总数
        r = await db.execute(
            text("SELECT COUNT(*) FROM task_packages WHERE assignee=:u"),
            {"u": username})
        counts.my_packages = r.fetchone()[0]
        # 已完成任务
        r = await db.execute(
            text("SELECT COUNT(*) FROM tasks WHERE assignee=:u AND status='已完成'"),
            {"u": username})
        counts.completed_tasks = r.fetchone()[0]
        # 退回修改的任务
        r = await db.execute(
            text("SELECT COUNT(*) FROM tasks WHERE assignee=:u AND status='退回修改'"),
            {"u": username})
        counts.returned_tasks = r.fetchone()[0]
        # 待复核的任务（已提交复核，等待复核员审核）
        r = await db.execute(
            text("SELECT COUNT(*) FROM tasks WHERE assignee=:u AND status IN ('待复核', '更正待复核')"),
            {"u": username})
        counts.review_pending_tasks = r.fetchone()[0]

    # ── 复核员 ──
    elif role == "复核员":
        # 待复核记录
        r = await db.execute(
            text("""SELECT COUNT(*) FROM records r
                    JOIN tasks t ON t.task_no=r.task_no
                    WHERE t.reviewer=:u AND r.status='待复核'"""),
            {"u": username})
        counts.pending_reviews = r.fetchone()[0]
        # 已复核记录
        r = await db.execute(
            text("""SELECT COUNT(*) FROM records r
                    JOIN tasks t ON t.task_no=r.task_no
                    WHERE t.reviewer=:u AND r.status='已复核'"""),
            {"u": username})
        counts.completed_tasks = r.fetchone()[0]

    # ── 质量负责人 ──
    elif role == "质量负责人":
        r = await db.execute(
            text("SELECT COUNT(*) FROM reports WHERE quality_inspector=:u AND status='待签发'"),
            {"u": username})
        counts.pending_reports = r.fetchone()[0]
        r = await db.execute(
            text("SELECT COUNT(*) FROM reports WHERE quality_inspector=:u AND status='已发布'"),
            {"u": username})
        counts.completed_tasks = r.fetchone()[0]

    # ── 管理员 / 样品管理员 ──
    if role in ("管理员", "样品管理员"):
        r = await db.execute(text("SELECT COUNT(*) FROM commissions"))
        counts.total_commissions = r.fetchone()[0]
        r = await db.execute(text("SELECT COUNT(*) FROM samples"))
        counts.total_samples = r.fetchone()[0]
        r = await db.execute(
            text("SELECT COUNT(*) FROM task_packages WHERE status='待接收'"))
        counts.pending_packages = r.fetchone()[0]
        r = await db.execute(
            text("SELECT COUNT(*) FROM records WHERE status='待复核'"))
        counts.pending_reviews = r.fetchone()[0]

    return counts
