"""单位信息库 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/organizations", tags=["单位信息库"])


class OrgOut(BaseModel):
    id: int
    org_code: str | None
    org_name: str
    short_name: str | None
    is_client: bool
    is_manufacturer: bool
    is_contract_manufacturer: bool
    address: str | None
    contact: str | None
    phone: str | None
    credit_code: str | None
    enabled: bool


class OrgCreate(BaseModel):
    org_code: str | None = None
    org_name: str = Field(..., min_length=1)
    short_name: str | None = None
    is_client: bool = False
    is_manufacturer: bool = False
    is_contract_manufacturer: bool = False
    address: str | None = None
    contact: str | None = None
    phone: str | None = None
    credit_code: str | None = None
    notes: str | None = None


@router.get("", response_model=list[OrgOut])
async def list_organizations(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    org_type: str | None = Query(None, description="client / manufacturer"),
    limit: int = Query(100, le=500),
):
    """单位列表"""
    where = "WHERE enabled=TRUE"
    params: dict = {}
    if org_type == "client":
        where += " AND is_client=TRUE"
    elif org_type == "manufacturer":
        where += " AND (is_manufacturer=TRUE OR is_contract_manufacturer=TRUE)"

    result = await db.execute(
        text(f"SELECT id, org_code, org_name, short_name, is_client, is_manufacturer, "
             f"is_contract_manufacturer, address, contact, phone, credit_code, enabled "
             f"FROM organizations {where} ORDER BY id LIMIT :limit"),
        {**params, "limit": limit},
    )
    return [
        OrgOut(
            id=r[0], org_code=r[1], org_name=r[2], short_name=r[3],
            is_client=r[4], is_manufacturer=r[5], is_contract_manufacturer=r[6],
            address=r[7], contact=r[8], phone=r[9], credit_code=r[10], enabled=r[11],
        )
        for r in result.fetchall()
    ]


@router.post("", response_model=OrgOut)
async def create_organization(
    body: OrgCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """新建单位"""
    result = await db.execute(
        text("""
            INSERT INTO organizations (org_code, org_name, short_name, is_client, is_manufacturer,
              is_contract_manufacturer, address, contact, phone, credit_code, notes, enabled, created_at, updated_at)
            VALUES (:oc, :on, :sn, :ic, :im, :icm, :ad, :co, :ph, :cc, :nt, TRUE, now(), now())
            RETURNING id
        """),
        {
            "oc": body.org_code, "on": body.org_name, "sn": body.short_name,
            "ic": body.is_client, "im": body.is_manufacturer, "icm": body.is_contract_manufacturer,
            "ad": body.address, "co": body.contact, "ph": body.phone,
            "cc": body.credit_code, "nt": body.notes,
        },
    )
    row = result.fetchone()
    return OrgOut(
        id=row[0], org_code=body.org_code, org_name=body.org_name,
        short_name=body.short_name, is_client=body.is_client,
        is_manufacturer=body.is_manufacturer,
        is_contract_manufacturer=body.is_contract_manufacturer,
        address=body.address, contact=body.contact, phone=body.phone,
        credit_code=body.credit_code, enabled=True,
    )


class OrgUpdate(BaseModel):
    org_code: str | None = None
    org_name: str | None = None
    short_name: str | None = None
    is_client: bool | None = None
    is_manufacturer: bool | None = None
    is_contract_manufacturer: bool | None = None
    address: str | None = None
    contact: str | None = None
    phone: str | None = None
    credit_code: str | None = None
    notes: str | None = None
    enabled: bool | None = None


@router.put("/{org_id}")
async def update_organization(
    org_id: int,
    body: OrgUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """编辑单位信息"""
    existing = await db.execute(
        text("SELECT 1 FROM organizations WHERE id=:i"), {"i": org_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="单位不存在")

    updates = []
    params: dict = {"id": org_id}
    for field in ["org_code", "org_name", "short_name", "is_client", "is_manufacturer",
                   "is_contract_manufacturer", "address", "contact", "phone", "credit_code", "notes", "enabled"]:
        value = getattr(body, field, None)
        if value is not None:
            updates.append(f"{field}=:{field}")
            params[field] = value

    if updates:
        params["id"] = org_id
        await db.execute(
            text(f"UPDATE organizations SET {', '.join(updates)}, updated_at=now() WHERE id=:id"),
            params,
        )

    return {"message": "单位信息已更新"}


@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员"))],
):
    """删除单位（软删除，管理员）"""
    result = await db.execute(
        text("UPDATE organizations SET enabled=FALSE, updated_at=now() WHERE id=:i AND enabled=TRUE"),
        {"i": org_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="单位不存在或已停用")
    return {"message": "单位已停用"}
