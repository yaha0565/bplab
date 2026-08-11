"""原始记录 API — 完整复核流程"""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user, get_db, require_role
from app.services.audit_service import write_audit_log, log_operation

router = APIRouter(prefix="/records", tags=["原始记录"])


class RecordBrief(BaseModel):
    record_no: str
    task_no: str
    version: int
    experiment: str | None
    status: str
    owner: str | None
    created_at: str | None


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _report_no_for_task(task_no: str) -> str:
    """报告编号 = R + task_no去掉BP前缀"""
    return "R" + task_no[2:] if task_no.startswith("BP") else f"R{task_no}"


async def _ensure_report_for_task(task_no: str, db: AsyncSession) -> str | None:
    """复核通过后自动生成检验报告初稿（状态=待质量审核）"""
    # 查任务信息
    task_result = await db.execute(
        text("""
            SELECT t.commission_no, t.experiment, t.assignee, t.reviewer,
                   t.quality_inspector, t.package_no
            FROM tasks t
            WHERE t.task_no = :t
        """),
        {"t": task_no},
    )
    task_row = task_result.fetchone()
    if not task_row:
        return None

    # 查最新锁定记录
    locked = await db.execute(
        text("""
            SELECT version, template_version, sop_version, payload
            FROM records
            WHERE record_no = :r AND status = '已锁定'
            ORDER BY version DESC LIMIT 1
        """),
        {"r": task_no},
    )
    locked_row = locked.fetchone()
    if not locked_row:
        return None

    # 查是否有已存在的报告
    existing = await db.execute(
        text("SELECT report_no, status FROM reports WHERE task_no = :t"),
        {"t": task_no},
    )
    existing_row = existing.fetchone()

    # 查管理员作为默认批准人
    admin_result = await db.execute(
        text("SELECT username FROM users WHERE role = '管理员' AND enabled = TRUE ORDER BY username LIMIT 1")
    )
    admin_row = admin_result.fetchone()
    approver_username = admin_row[0] if admin_row else ""

    # 查质量负责人（从tasks表）
    quality_inspector = task_row[4] or ""

    source_versions = json.dumps({
        task_no: locked_row[0],
        "record_template": locked_row[1] or "",
        "sop": locked_row[2] or "",
    }, ensure_ascii=False)

    payload = locked_row[3] if isinstance(locked_row[3], dict) else (json.loads(locked_row[3]) if locked_row[3] else {})

    if existing_row:
        # 已有报告：如果是退回状态，重置为待质量审核
        if existing_row[1] in ("质量退回", "复核退回"):
            await db.execute(
                text("""
                    UPDATE reports SET status = '待质量审核',
                        source_versions = :sv,
                        conclusion = :conc, notes = :notes,
                        updated_at = localtimestamp
                    WHERE report_no = :r
                """),
                {
                    "sv": source_versions,
                    "conc": payload.get("report_conclusion", ""),
                    "notes": payload.get("report_summary", ""),
                    "r": existing_row[0],
                },
            )
            await db.execute(
                text("""
                    INSERT INTO report_actions (report_no, actor, action, comment, created_at)
                    VALUES (:r, 'system', '根据新记录版本重生成初稿', :c, localtimestamp)
                """),
                {"r": existing_row[0], "c": f"原始记录V{locked_row[0]}"},
            )
            await write_audit_log(db, "report", existing_row[0], "system", "根据新记录版本重生成初稿",
                                  comment=f"原始记录V{locked_row[0]}")
        return existing_row[0]

    # 新建报告
    report_no = _report_no_for_task(task_no)

    await db.execute(
        text("""
            INSERT INTO reports (
                report_no, commission_no, task_no, status,
                tester, verifier, quality_inspector, approver,
                source_versions, report_category, sample_statement,
                conclusion, notes, created_at, updated_at
            ) VALUES (
                :rn, :cn, :tn, '待质量审核',
                :tr, :vf, :qi, :ap,
                :sv, '委托检验', '',
                :conc, :notes, localtimestamp, localtimestamp
            )
        """),
        {
            "rn": report_no, "cn": task_row[0], "tn": task_no,
            "tr": task_row[2] or "",
            "vf": task_row[3] or "", "qi": quality_inspector,
            "ap": approver_username,
            "sv": source_versions,
            "conc": payload.get("report_conclusion", ""),
            "notes": payload.get("report_summary", ""),
        },
    )

    await db.execute(
        text("""
            INSERT INTO report_actions (report_no, actor, action, comment, created_at)
            VALUES (:r, 'system', '自动生成报告初稿', '原始记录复核通过后自动生成', localtimestamp)
        """),
        {"r": report_no},
    )
    await write_audit_log(db, "report", report_no, "system", "自动生成报告初稿",
                          comment="原始记录复核通过后自动生成")

    return report_no


# ═══════════════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════════════

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
        text("SELECT experiment, experiment_code, assignee, status FROM tasks WHERE task_no=:t"),
        {"t": body.task_no},
    )
    task = task_result.fetchone()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task[2] != user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能提交自己的实验记录")

    record_no = body.task_no

    # 查当前最大版本号及最新记录状态
    ver_result = await db.execute(
        text("SELECT COALESCE(MAX(version), 0) FROM records WHERE record_no=:r"),
        {"r": record_no},
    )
    max_version = ver_result.fetchone()[0]

    prev_status = None
    if max_version > 0:
        prev = await db.execute(
            text("SELECT status, id FROM records WHERE record_no=:r AND version=:v"),
            {"r": record_no, "v": max_version},
        )
        prev_row = prev.fetchone()
        if prev_row:
            prev_status = prev_row[0]
            prev_id = prev_row[1]

    # ── 版本号规则 ──
    # 草稿反复保存 → 同一版本 (UPDATE)，不升版
    # 退回后由 review_record 创建新草稿版本 → 用户在该版本上反复保存仍为同一版本
    # 只有 review_record 的退回操作才触发升版

    # 检查历史上是否有退回记录（用于 change_reason / new_status 判定）
    was_rejected = False
    if max_version > 0:
        rejected_check = await db.execute(
            text("SELECT 1 FROM records WHERE record_no=:r AND status IN ('复核退回','质量退回') LIMIT 1"),
            {"r": record_no},
        )
        was_rejected = rejected_check.fetchone() is not None

    if max_version > 0 and prev_status == "草稿":
        version = max_version       # 覆盖当前草稿（含复核退回后由 review_record 创建的新草稿）
    else:
        version = max_version + 1 if max_version > 0 else 1

    if body.submit_for_review:
        if prev_status in ("复核退回", "质量退回"):
            new_status = "更正待复核"
        elif version > 1:
            new_status = "更正待复核"
        else:
            new_status = "待复核"
    else:
        new_status = "草稿"

    # 将报告摘要/结论/自检标记合并到 business_record 中，统一存入 payload
    merged_record = dict(body.business_record)
    merged_record["report_summary"] = body.report_summary
    merged_record["report_conclusion"] = body.report_conclusion
    merged_record["tester_self_check"] = body.tester_self_check
    payload_json = json.dumps(merged_record, ensure_ascii=False, default=str)

    # 模板/SOP版本
    tm_version = "A/0"
    sm_version = "A/0"
    if max_version > 0:
        prev_versions = await db.execute(
            text("SELECT template_version, sop_version FROM records WHERE record_no=:r ORDER BY version DESC LIMIT 1"),
            {"r": record_no},
        )
        pv_row = prev_versions.fetchone()
        if pv_row:
            tm_version = pv_row[0] or "A/0"
            sm_version = pv_row[1] or "A/0"

    change_reason = ""
    if was_rejected:
        last_review = await db.execute(
            text("""
                SELECT comment, correction_fields FROM reviews
                WHERE record_no=:r AND decision='退回'
                ORDER BY reviewed_at DESC LIMIT 1
            """),
            {"r": record_no},
        )
        lr = last_review.fetchone()
        if lr:
            cf = json.loads(lr[1]) if isinstance(lr[1], str) else (lr[1] or [])
            change_reason = f"复核退回二次编辑：{'；'.join(cf)}；{lr[0] or ''}"

    # ── 持久化：草稿覆盖同一版本(UPDATE)，退回后编辑新建版本(INSERT) ──
    if max_version > 0 and prev_status == "草稿":
        # 覆盖同一草稿版本
        await db.execute(
            text("""
                UPDATE records SET
                    payload = CAST(:pl AS jsonb),
                    status = :st,
                    tester_signed_at = CASE WHEN :sfr THEN localtimestamp ELSE tester_signed_at END,
                    change_reason = :cr,
                    updated_at = localtimestamp
                WHERE record_no = :rn AND version = :v
            """),
            {
                "rn": record_no, "v": version, "st": new_status,
                "pl": payload_json, "cr": change_reason,
                "sfr": body.submit_for_review,
            },
        )
    else:
        await db.execute(
            text("""
                INSERT INTO records (record_no, task_no, version, experiment, owner, status,
                  payload,
                  template_version, sop_version, change_reason, tester_signed_at,
                  created_at, updated_at)
                VALUES (:rn, :tn, :v, :ex, :ow, :st, CAST(:pl AS jsonb),
                  :tv, :sv, :cr,
                  CASE WHEN :sfr THEN localtimestamp ELSE NULL END,
                  localtimestamp, localtimestamp)
            """),
            {
                "rn": record_no, "tn": body.task_no, "v": version,
                "ex": task[0], "ow": user["username"], "st": new_status,
                "pl": payload_json,
                "tv": tm_version, "sv": sm_version, "cr": change_reason,
                "sfr": body.submit_for_review,
            },
        )

    # 如果提交复核，更新任务状态，自动记录结束时间，并同步任务包状态
    if body.submit_for_review:
        await db.execute(
            text("""
                UPDATE tasks SET status = :st,
                    experiment_ended_at = COALESCE(experiment_ended_at, localtimestamp),
                    reviewer = COALESCE(tasks.reviewer, tp.reviewer),
                    updated_at = localtimestamp
                FROM task_packages tp
                WHERE tasks.task_no = :t AND tasks.package_no = tp.package_no
            """),
            {"st": new_status, "t": body.task_no},
        )

        # 同步任务包状态：当包内所有任务都已提交复核/已复核时，更新任务包
        await db.execute(
            text("""
                UPDATE task_packages tp SET status =
                    CASE
                        WHEN (SELECT COUNT(*) FROM tasks t
                              WHERE t.package_no = tp.package_no
                                AND t.status NOT IN ('待复核','更正待复核','已复核','已锁定'))
                             = 0
                        THEN '已复核'
                        ELSE tp.status
                    END,
                    updated_at = localtimestamp
                WHERE tp.package_no = (
                    SELECT t2.package_no FROM tasks t2 WHERE t2.task_no = :t
                )
            """),
            {"t": body.task_no},
        )

    # 审计日志
    comm_result = await db.execute(
        text("SELECT commission_no FROM tasks WHERE task_no=:t"),
        {"t": body.task_no},
    )
    comm_row = comm_result.fetchone()
    if comm_row:
        action = "提交复核" if body.submit_for_review else "保存草稿"
        await log_operation(db, "record", record_no, user, action,
                             commission_no=comm_row[0],
                             comment=f"版本V{version} 实验:{task[0]}")

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
    correction_fields: list[str] = []


@router.post("/{record_no}/review")
async def review_record(
    record_no: str,
    body: ReviewRecordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(require_role("复核员"))],
):
    """复核原始记录 — 通过则锁定并自动生成报告；退回则创建新草稿版本"""
    # 获取最新版本
    rec_result = await db.execute(
        text("""
            SELECT r.task_no, r.version, r.status, r.experiment, r.owner,
                   r.payload, r.template_version, r.sop_version
            FROM records r
            WHERE r.record_no = :r
            ORDER BY r.version DESC LIMIT 1
        """),
        {"r": record_no},
    )
    record = rec_result.fetchone()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")

    # 允许"待复核"和"更正待复核"
    if record[2] not in ("待复核", "更正待复核"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail=f"记录状态为'{record[2]}'，无法复核")

    task_no = record[0]
    version = record[1]

    # 验证复核员权限
    task_check = await db.execute(
        text("""
            SELECT COALESCE(t.reviewer, tp.reviewer) AS reviewer,
                   t.assignee, t.package_no
            FROM tasks t
            JOIN task_packages tp ON tp.package_no = t.package_no
            WHERE t.task_no = :t
        """),
        {"t": task_no},
    )
    task_row = task_check.fetchone()
    if not task_row or task_row[0] != user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail="只能复核分配给自己的任务")
    if task_row[1] == user["username"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail="实验人员不得复核本人完成的实验")

    # 退回时必须填写意见和指定修改字段
    if body.decision == "退回":
        if not body.comment.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail="退回实验员修改时必须填写复核意见")
        if not body.correction_fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail="退回实验员修改时必须至少指定一个需要修改的字段")

    # 插入复核记录
    correction_json = json.dumps(body.correction_fields, ensure_ascii=False)
    await db.execute(
        text("""
            INSERT INTO reviews (record_no, version, reviewer, decision, comment,
              correction_fields, reviewed_at)
            VALUES (:rn, :v, :rv, :d, :c, CAST(:cf AS jsonb), localtimestamp)
        """),
        {
            "rn": record_no, "v": version, "rv": user["username"],
            "d": body.decision, "c": body.comment, "cf": correction_json,
        },
    )

    if body.decision == "通过":
        # ── 通过：锁定记录，更新任务为"已复核"，自动生成报告 ──
        await db.execute(
            text("""
                UPDATE records SET status = '已锁定',
                    reviewer_signed_at = localtimestamp,
                    updated_at = localtimestamp
                WHERE record_no = :r AND version = :v
            """),
            {"r": record_no, "v": version},
        )

        await db.execute(
            text("UPDATE tasks SET status = '已复核', updated_at = localtimestamp WHERE task_no = :t"),
            {"t": task_no},
        )

        # 同步任务包状态
        await db.execute(
            text("""
                UPDATE task_packages SET status = '已复核', updated_at = localtimestamp
                WHERE package_no = (SELECT t.package_no FROM tasks t WHERE t.task_no = :t)
                  AND NOT EXISTS (
                    SELECT 1 FROM tasks t2
                    WHERE t2.package_no = task_packages.package_no
                      AND t2.status NOT IN ('已复核', '已锁定')
                  )
            """),
            {"t": task_no},
        )

        # 自动生成报告
        await _ensure_report_for_task(task_no, db)

        # 审计日志
        comm_result = await db.execute(
            text("SELECT commission_no FROM tasks WHERE task_no=:t"),
            {"t": task_no},
        )
        comm_row = comm_result.fetchone()
        if comm_row:
            await log_operation(db, "record", record_no, user, "复核通过",
                                 commission_no=comm_row[0],
                                 comment=f"版本V{version} 实验:{record[3]}")

        return {"message": "复核通过，记录已锁定，报告已自动生成", "status": "已锁定"}

    else:
        # ── 退回：标记当前版本为复核退回，创建新草稿版本 ──
        await db.execute(
            text("""
                UPDATE records SET status = '复核退回',
                    updated_at = localtimestamp
                WHERE record_no = :r AND version = :v
            """),
            {"r": record_no, "v": version},
        )

        await db.execute(
            text("UPDATE tasks SET status = '退回修改', updated_at = localtimestamp WHERE task_no = :t"),
            {"t": task_no},
        )

        # 同步任务包状态：有退回的任务包标记为"部分退回"
        await db.execute(
            text("""
                UPDATE task_packages SET status = '部分退回', updated_at = localtimestamp
                WHERE package_no = (SELECT t.package_no FROM tasks t WHERE t.task_no = :t)
            """),
            {"t": task_no},
        )

        # 创建新草稿版本，复制原payload供实验员修改
        next_version = version + 1
        # 确认不冲突
        existing_next = await db.execute(
            text("SELECT 1 FROM records WHERE record_no=:r AND version=:v"),
            {"r": record_no, "v": next_version},
        )
        if existing_next.fetchone():
            max_ver = await db.execute(
                text("SELECT COALESCE(MAX(version), 0) FROM records WHERE record_no=:r"),
                {"r": record_no},
            )
            next_version = max_ver.fetchone()[0] + 1

        change_reason = f"复核退回二次编辑：{'；'.join(body.correction_fields)}；{body.comment}"
        payload_raw = record[5]
        payload_str = json.dumps(
            payload_raw if isinstance(payload_raw, dict) else (json.loads(payload_raw) if payload_raw else {}),
            ensure_ascii=False, default=str,
        )

        await db.execute(
            text("""
                INSERT INTO records (record_no, task_no, version, experiment, owner, status,
                  payload, template_version, sop_version, change_reason,
                  created_at, updated_at)
                VALUES (:rn, :tn, :v, :ex, :ow, '草稿',
                  CAST(:pl AS jsonb), :tv, :sv, :cr,
                  localtimestamp, localtimestamp)
            """),
            {
                "rn": record_no, "tn": task_no, "v": next_version,
                "ex": record[3], "ow": record[4],
                "pl": payload_str,
                "tv": record[6] or "A/0", "sv": record[7] or "A/0",
                "cr": change_reason,
            },
        )

        # 审计日志
        comm_result = await db.execute(
            text("SELECT commission_no FROM tasks WHERE task_no=:t"),
            {"t": task_no},
        )
        comm_row = comm_result.fetchone()
        if comm_row:
            await log_operation(db, "record", record_no, user, "复核退回",
                                 commission_no=comm_row[0],
                                 comment=f"版本V{version}→V{next_version} 原因:{body.comment}")

        return {
            "message": f"复核退回，新草稿版本V{next_version}已创建",
            "status": "复核退回",
            "next_version": next_version,
            "correction_fields": body.correction_fields,
        }


# ── 待复核列表 ──

@router.get("/pending-review", response_model=list[RecordBrief])
async def pending_reviews(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(50, le=200),
):
    """待复核的记录（含"待复核"和"更正待复核"）"""
    result = await db.execute(
        text("""
            SELECT r.record_no, r.task_no, r.version, r.experiment, r.status, r.owner, r.created_at
            FROM records r
            JOIN tasks t ON t.task_no = r.task_no
            LEFT JOIN task_packages tp ON tp.package_no = t.package_no
            WHERE COALESCE(t.reviewer, tp.reviewer) = :reviewer
              AND r.status IN ('待复核', '更正待复核')
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


# ── 查询接口 ──

@router.get("/{record_no}/versions")
async def record_versions(
    record_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """某记录的所有版本"""
    result = await db.execute(
        text("""
            SELECT id, record_no, task_no, version, experiment, owner, status,
                   template_version, sop_version, change_reason,
                   tester_signed_at, reviewer_signed_at, quality_signed_at, created_at
            FROM records WHERE record_no = :r ORDER BY version DESC
        """),
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
    """获取某版本的记录详情（含 payload 和审核历史）"""
    result = await db.execute(
        text("SELECT * FROM records WHERE record_no = :r AND version = :v"),
        {"r": record_no, "v": version},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    record = dict(zip(result.keys(), row))

    # 审核历史
    reviews_result = await db.execute(
        text("""
            SELECT reviewer, decision, comment, correction_fields, reviewed_at
            FROM reviews WHERE record_no = :r AND version = :v
            ORDER BY reviewed_at
        """),
        {"r": record_no, "v": version},
    )
    record["reviews"] = [dict(zip(reviews_result.keys(), r)) for r in reviews_result.fetchall()]

    return record


# ═══════════════════════════════════════════════════════════════
# ── Word 预览 / 导出 ──
# ═══════════════════════════════════════════════════════════════

from fastapi.responses import HTMLResponse, Response


@router.get("/{record_no}/v{version}/preview", response_class=HTMLResponse)
async def preview_record_word(
    record_no: str,
    version: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """复核员/质量负责人预览填入数据的受控Word — 返回HTML审核阅读器"""
    # 查询记录
    rec_result = await db.execute(
        text("SELECT * FROM records WHERE record_no=:r AND version=:v"),
        {"r": record_no, "v": version},
    )
    row = rec_result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    record = dict(zip(rec_result.keys(), row))

    # 权限检查：复核员/质量负责人/管理员可预览
    role = user.get("role", "")
    if role not in ("复核员", "质量负责人", "管理员", "样品管理员"):
        if record.get("owner") != user["username"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权预览此记录")

    # 查询关联任务
    task_no = record.get("task_no", "")
    task = None
    if task_no:
        t_result = await db.execute(
            text("SELECT * FROM tasks WHERE task_no=:t"), {"t": task_no}
        )
        t_row = t_result.fetchone()
        if t_row:
            task = dict(zip(t_result.keys(), t_row))

    # 生成 DOCX
    try:
        from app.services.record_word_engine import export_record_docx
        from app.services.docx_preview import docx_review_html
        docx_bytes = export_record_docx(
            record, task,
            template_dir=settings.TEMPLATE_DIR,
            signature_dir=settings.SIGNATURE_DIR,
        )
        title = f"{record.get('experiment','原始记录')} — {record_no} V{version}"
        html = docx_review_html(docx_bytes, title)
        return HTMLResponse(content=html)
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"预览服务不可用：{e}",
        )


@router.get("/{record_no}/v{version}/export")
async def export_record_docx_endpoint(
    record_no: str,
    version: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """导出填入数据的受控Word文档（仅管理员/质量负责人可下载）"""
    role = user.get("role", "")
    if role not in ("管理员", "质量负责人", "复核员"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权下载此记录")

    rec_result = await db.execute(
        text("SELECT * FROM records WHERE record_no=:r AND version=:v"),
        {"r": record_no, "v": version},
    )
    row = rec_result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    record = dict(zip(rec_result.keys(), row))

    task_no = record.get("task_no", "")
    task = None
    if task_no:
        t_result = await db.execute(
            text("SELECT * FROM tasks WHERE task_no=:t"), {"t": task_no}
        )
        t_row = t_result.fetchone()
        if t_row:
            task = dict(zip(t_result.keys(), t_row))

    try:
        from app.services.record_word_engine import export_record_docx
        docx_bytes = export_record_docx(
            record, task,
            template_dir=settings.TEMPLATE_DIR,
            signature_dir=settings.SIGNATURE_DIR,
        )
        filename = f"{record_no}_V{version}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"导出服务不可用：{e}",
        )
