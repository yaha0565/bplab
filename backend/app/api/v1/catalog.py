"""样品资料库 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import json

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/catalog", tags=["样品资料库"])


class SampleCatalogOut(BaseModel):
    id: int
    sample_code: str | None
    sample_name: str
    model: str
    material_name: str
    process: str | None
    category: str | None
    unit: str | None
    experiment_codes: list | None
    enabled: bool


class SampleCatalogCreate(BaseModel):
    sample_name: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    material_name: str = Field(..., min_length=1)
    sample_code: str | None = None
    process: str | None = None
    material_suffix: str | None = None
    source_sequence: str | None = None
    category: str | None = None
    unit: str | None = None
    experiment_codes: list[str] | None = None
    notes: str | None = None


@router.get("", response_model=list[SampleCatalogOut])
async def list_catalog(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    search: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    """样品目录列表"""
    where = "WHERE enabled=TRUE"
    params: dict = {}
    if search:
        where += " AND (sample_name ILIKE :s OR sample_code ILIKE :s OR material_name ILIKE :s)"
        params["s"] = f"%{search}%"

    result = await db.execute(
        text(f"SELECT id, sample_code, sample_name, model, material_name, process, category, unit, experiment_codes, enabled "
             f"FROM sample_catalog {where} ORDER BY id LIMIT :limit"),
        {**params, "limit": limit},
    )
    return [
        SampleCatalogOut(
            id=r[0], sample_code=r[1], sample_name=r[2], model=r[3],
            material_name=r[4], process=r[5], category=r[6], unit=r[7],
            experiment_codes=r[8], enabled=r[9],
        )
        for r in result.fetchall()
    ]


@router.post("", response_model=SampleCatalogOut, status_code=201)
async def create_catalog_entry(
    body: SampleCatalogCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """新增样品资料（管理员、样品管理员）"""
    result = await db.execute(
        text("""
            INSERT INTO sample_catalog (sample_code, sample_name, model, material_name, process,
              material_suffix, source_sequence, category, unit, experiment_codes, notes)
            VALUES (:sc, :sn, :md, :mn, :pr, :ms, :ss, :ct, :un, CAST(:ec AS jsonb), :nt)
            RETURNING id
        """),
        {
            "sc": body.sample_code, "sn": body.sample_name, "md": body.model,
            "mn": body.material_name, "pr": body.process, "ms": body.material_suffix,
            "ss": body.source_sequence, "ct": body.category, "un": body.unit,
            "ec": json.dumps(body.experiment_codes or []), "nt": body.notes,
        },
    )
    new_id = result.fetchone()[0]
    return SampleCatalogOut(
        id=new_id, sample_code=body.sample_code, sample_name=body.sample_name,
        model=body.model, material_name=body.material_name, process=body.process,
        category=body.category, unit=body.unit,
        experiment_codes=body.experiment_codes or [], enabled=True,
    )


@router.delete("/{catalog_id}")
async def delete_catalog_entry(
    catalog_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """删除样品资料（软删除，管理员/样品管理员）"""
    result = await db.execute(
        text("UPDATE sample_catalog SET enabled=FALSE WHERE id=:i AND enabled=TRUE"),
        {"i": catalog_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="样品资料不存在或已停用")
    return {"message": "样品资料已停用"}
