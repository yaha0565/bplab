"""设备库 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/equipment", tags=["设备库"])


class EquipmentOut(BaseModel):
    management_no: str
    seq: int | None
    equipment_name: str
    model: str | None
    measuring_range: str | None
    manufacturer: str | None
    serial_no: str | None
    purchase_time: str | None
    calibration_time: str | None
    responsible: str | None
    equipment_class: str | None
    enabled: bool
    lifecycle_status: str | None
    notes: str | None


class EquipmentCreate(BaseModel):
    management_no: str = Field(..., min_length=1)
    equipment_name: str = Field(..., min_length=1)
    model: str | None = None
    measuring_range: str | None = None
    manufacturer: str | None = None
    serial_no: str | None = None
    purchase_time: str | None = None
    calibration_time: str | None = None
    responsible: str | None = None
    equipment_class: str | None = None
    lifecycle_status: str | None = None
    notes: str | None = None


@router.get("", response_model=list[EquipmentOut])
async def list_equipment(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    search: str | None = Query(None),
    equipment_class: str | None = Query(None),
    limit: int = Query(200, le=500),
):
    """设备列表"""
    where = "WHERE enabled=TRUE"
    params: dict = {}
    if search:
        where += " AND (equipment_name ILIKE :s OR management_no ILIKE :s OR model ILIKE :s)"
        params["s"] = f"%{search}%"
    if equipment_class:
        where += " AND equipment_class=:ec"
        params["ec"] = equipment_class

    result = await db.execute(
        text(f"SELECT management_no, seq, equipment_name, model, measuring_range, manufacturer, "
             f"serial_no, purchase_time, calibration_time, responsible, equipment_class, enabled, "
             f"lifecycle_status, notes FROM equipment_registry {where} ORDER BY seq LIMIT :limit"),
        {**params, "limit": limit},
    )
    return [
        EquipmentOut(
            management_no=r[0], seq=r[1], equipment_name=r[2], model=r[3],
            measuring_range=r[4], manufacturer=r[5], serial_no=r[6],
            purchase_time=r[7], calibration_time=r[8], responsible=r[9],
            equipment_class=r[10], enabled=r[11], lifecycle_status=r[12], notes=r[13],
        )
        for r in result.fetchall()
    ]


@router.post("", response_model=EquipmentOut, status_code=201)
async def create_equipment(
    body: EquipmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """新增设备（管理员、样品管理员）"""
    # 检查管理编号是否已存在
    existing = await db.execute(
        text("SELECT management_no FROM equipment_registry WHERE management_no=:mn"),
        {"mn": body.management_no},
    )
    if existing.fetchone():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="设备管理编号已存在")

    # 自动生成 seq
    seq_result = await db.execute(text("SELECT COALESCE(MAX(seq), 0) + 1 FROM equipment_registry"))
    next_seq = seq_result.fetchone()[0]

    await db.execute(
        text("""
            INSERT INTO equipment_registry (management_no, seq, equipment_name, model,
              measuring_range, manufacturer, serial_no, purchase_time, calibration_time,
              responsible, equipment_class, lifecycle_status, notes)
            VALUES (:mn, :sq, :en, :md, :mr, :mf, :sn, :pt, :ct, :rp, :ec, :ls, :nt)
        """),
        {
            "mn": body.management_no, "sq": next_seq, "en": body.equipment_name,
            "md": body.model, "mr": body.measuring_range, "mf": body.manufacturer,
            "sn": body.serial_no, "pt": body.purchase_time, "ct": body.calibration_time,
            "rp": body.responsible, "ec": body.equipment_class,
            "ls": body.lifecycle_status or "正常", "nt": body.notes,
        },
    )

    return EquipmentOut(
        management_no=body.management_no, seq=next_seq, equipment_name=body.equipment_name,
        model=body.model, measuring_range=body.measuring_range, manufacturer=body.manufacturer,
        serial_no=body.serial_no, purchase_time=body.purchase_time,
        calibration_time=body.calibration_time, responsible=body.responsible,
        equipment_class=body.equipment_class, enabled=True,
        lifecycle_status=body.lifecycle_status or "正常", notes=body.notes,
    )


@router.delete("/{management_no}")
async def delete_equipment(
    management_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """删除设备（软删除，管理员/样品管理员）"""
    result = await db.execute(
        text("UPDATE equipment_registry SET enabled=FALSE WHERE management_no=:mn AND enabled=TRUE"),
        {"mn": management_no},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在或已停用")
    return {"message": f"设备 {management_no} 已停用"}
