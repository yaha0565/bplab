"""系统初始化 API（管理员）"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/system", tags=["系统管理"])


@router.get("/health")
async def system_health(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员"))],
):
    """系统健康检查（管理员）"""
    # 数据库连接检查
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # 各表行数统计
    table_counts = {}
    tables = [
        "users", "organizations", "commissions", "sample_groups", "samples",
        "task_packages", "tasks", "records", "reports", "attachments",
        "equipment_registry", "sample_catalog", "experiment_methods",
        "audit_logs", "modification_logs", "notifications", "objections",
        "equipment_incidents", "hazardous_waste_records",
    ]
    for t in tables:
        try:
            r = await db.execute(text(f"SELECT COUNT(*) FROM {t}"))
            table_counts[t] = r.fetchone()[0]
        except Exception:
            table_counts[t] = -1

    return {
        "database_ok": db_ok,
        "table_counts": table_counts,
        "total_tables_with_data": sum(1 for c in table_counts.values() if c > 0),
    }


class InitRequest(BaseModel):
    confirm_text: str = Field(..., min_length=1)


@router.post("/initialize")
async def initialize_system(
    body: InitRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """系统初始化：清空所有业务数据，保留基础数据（用户、单位、方法、设备、样品目录）

    需要输入确认文字 "确认初始化系统" 进行二次确认。
    """
    if body.confirm_text.strip() != "确认初始化系统":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='确认文字错误，请输入"确认初始化系统"',
        )

    # 保留的表（不删除数据）
    keep_tables = [
        "users", "organizations", "experiment_methods",
        "sample_catalog", "equipment_registry", "experiment_config_versions",
        "experiment_config_fields", "experiment_config_columns",
        "experiment_config_photo_checkpoints", "experiment_config_prechecks",
        "experiment_config_validation_rules", "experiment_config_equipment",
        "device_presets", "experiment_equipment_bindings",
    ]

    # 待清空的业务表（按外键依赖排序：子表在前，父表在后）
    clear_tables = [
        "notifications",
        "objection_actions",
        "objections",
        "report_deliveries",
        "report_actions",
        "reports",
        "package_loans",
        "sample_events",
        "modification_logs",
        "audit_logs",
        "attachments",
        "records",
        "reviews",
        "tasks",
        "task_packages",
        "task_config_snapshots",
        "equipment_incidents",
        "hazardous_waste_records",
        "samples",
        "requested_tests",
        "sample_groups",
        "commissions",
        "sessions",
        "signatures",
    ]

    cleared = []
    for t in clear_tables:
        result = await db.execute(text(f"DELETE FROM {t}"))
        cleared.append(f"{t}: {result.rowcount} 行")

    return {
        "message": "系统初始化完成",
        "cleared_tables": cleared,
        "kept_tables": keep_tables,
        "operator": current_user["username"],
    }
