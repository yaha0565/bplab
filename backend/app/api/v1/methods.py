"""检测项目与方法库 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/methods", tags=["检测方法"])


class MethodOut(BaseModel):
    experiment_code: str
    experiment_name: str
    method_code: str
    standard: str | None
    category: str | None
    kind: str | None
    enabled: bool
    sort_order: int


class MethodCreate(BaseModel):
    experiment_code: str = Field(..., min_length=1, description="实验编码，如 I001")
    experiment_name: str = Field(..., min_length=1, description="实验名称，如 表面粗糙度检测")
    method_code: str = Field(..., min_length=1, description="方法编号，如 GB/T 1031-2009")
    standard: str | None = None
    category: str | None = None
    kind: str = Field(default="generic", description="实验类型")


@router.get("", response_model=list[MethodOut])
async def list_methods(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    enabled_only: bool = Query(True),
):
    """检测项目列表"""
    where = "WHERE enabled=TRUE" if enabled_only else ""
    result = await db.execute(
        text(f"SELECT experiment_code, experiment_name, method_code, standard, category, kind, enabled, sort_order "
             f"FROM experiment_methods {where} ORDER BY sort_order, experiment_code")
    )
    return [
        MethodOut(
            experiment_code=r[0], experiment_name=r[1], method_code=r[2],
            standard=r[3], category=r[4], kind=r[5], enabled=r[6], sort_order=r[7],
        )
        for r in result.fetchall()
    ]


@router.post("", response_model=MethodOut, status_code=201)
async def create_method(
    body: MethodCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """新增检测项目（管理员、样品管理员）"""
    # 检查实验编码是否已存在
    existing = await db.execute(
        text("SELECT 1 FROM experiment_methods WHERE experiment_code=:c"),
        {"c": body.experiment_code},
    )
    if existing.fetchone():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="实验编码已存在")

    # 自动排序号
    seq_result = await db.execute(text("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM experiment_methods"))
    next_seq = seq_result.fetchone()[0]

    await db.execute(
        text("""
            INSERT INTO experiment_methods (experiment_code, experiment_name, method_code,
              standard, category, kind, enabled, sort_order, created_at, updated_at)
            VALUES (:ec, :en, :mc, :st, :ct, :kd, TRUE, :so, now(), now())
        """),
        {
            "ec": body.experiment_code, "en": body.experiment_name, "mc": body.method_code,
            "st": body.standard, "ct": body.category, "kd": body.kind, "so": next_seq,
        },
    )

    return MethodOut(
        experiment_code=body.experiment_code,
        experiment_name=body.experiment_name,
        method_code=body.method_code,
        standard=body.standard,
        category=body.category,
        kind=body.kind,
        enabled=True,
        sort_order=next_seq,
    )


@router.delete("/{experiment_code}")
async def delete_method(
    experiment_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """删除检测项目（软删除，管理员/样品管理员）"""
    result = await db.execute(
        text("UPDATE experiment_methods SET enabled=FALSE, updated_at=now() WHERE experiment_code=:c AND enabled=TRUE"),
        {"c": experiment_code},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="检测项目不存在或已停用")
    return {"message": f"检测项目 {experiment_code} 已停用"}


@router.get("/categories")
async def method_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """获取所有检测类别"""
    result = await db.execute(
        text("SELECT DISTINCT category FROM experiment_methods WHERE enabled=TRUE AND category IS NOT NULL ORDER BY category")
    )
    return [r[0] for r in result.fetchall()]
