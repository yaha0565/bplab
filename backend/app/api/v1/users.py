"""用户管理 API（管理员）"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import log_operation

from app.core.deps import get_current_user, get_db, require_role
from app.core.security import hash_password

router = APIRouter(prefix="/users", tags=["用户管理"])


class UserOut(BaseModel):
    username: str
    display_name: str
    role: str
    enabled: bool
    created_at: str | None = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern=r"^(管理员|样品管理员|实验员|复核员|质量负责人)$")


class UserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=8)


@router.get("", response_model=list[UserOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员", "样品管理员"))],
):
    """列出全部用户（管理员、样品管理员可查看，用于任务包分配时选择实验员/复核员）"""
    result = await db.execute(
        text("SELECT username, display_name, role, enabled, created_at FROM users ORDER BY created_at")
    )
    return [
        UserOut(username=r[0], display_name=r[1], role=r[2], enabled=r[3],
                created_at=str(r[4]) if r[4] else None)
        for r in result.fetchall()
    ]


@router.post("", response_model=UserOut)
async def create_user(
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(require_role("管理员"))],
):
    """添加用户"""
    exists = await db.execute(text("SELECT 1 FROM users WHERE username=:u"), {"u": body.username})
    if exists.fetchone():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    await db.execute(
        text("INSERT INTO users (username, display_name, password_hash, role, enabled, created_at) VALUES (:u, :d, :p, :r, TRUE, localtimestamp)"),
        {"u": body.username, "d": body.display_name, "p": hash_password(body.password), "r": body.role},
    )
    await log_operation(db, "user", body.username, _user, "创建用户",
                         comment=f"角色:{body.role} 姓名:{body.display_name}")
    return UserOut(username=body.username, display_name=body.display_name, role=body.role, enabled=True)


@router.put("/{username}/password")
async def reset_password(
    username: str,
    body: UserResetPassword,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """重置用户密码（管理员）"""
    result = await db.execute(
        text("UPDATE users SET password_hash=:p WHERE username=:u"),
        {"p": hash_password(body.new_password), "u": username},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    await log_operation(db, "user", username, current_user, "重置密码")
    return {"message": "密码已重置"}


class UserUpdateRole(BaseModel):
    role: str = Field(..., pattern=r"^(管理员|样品管理员|实验员|复核员|质量负责人)$")


@router.put("/{username}/role")
async def update_user_role(
    username: str,
    body: UserUpdateRole,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """修改用户角色"""
    if username == current_user["username"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能修改自己的角色")

    result = await db.execute(
        text("UPDATE users SET role=:r WHERE username=:u"),
        {"r": body.role, "u": username},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    await log_operation(db, "user", username, current_user, "修改角色",
                         comment=f"新角色:{body.role}")
    return {"message": "角色已更新"}


@router.delete("/{username}")
async def delete_user(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """删除用户（管理员，不可删除自己）"""
    if username == current_user["username"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己的账号")

    # 检查用户是否存在
    exists = await db.execute(text("SELECT 1 FROM users WHERE username=:u"), {"u": username})
    if not exists.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 解除该用户负责的任务包（置空 assignee/reviewer）
    await db.execute(
        text("UPDATE task_packages SET assignee=NULL WHERE assignee=:u"),
        {"u": username},
    )
    await db.execute(
        text("UPDATE task_packages SET reviewer=NULL WHERE reviewer=:u"),
        {"u": username},
    )

    # 删除用户
    await db.execute(text("DELETE FROM users WHERE username=:u"), {"u": username})
    await log_operation(db, "user", username, current_user, "删除用户")
    return {"message": f"用户 {username} 已删除"}
