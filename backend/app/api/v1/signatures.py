"""电子签名管理 API"""
from __future__ import annotations

import os
import hashlib
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user, get_db, require_role
from app.services.audit_service import log_operation

router = APIRouter(prefix="/signatures", tags=["电子签名"])


class SignatureOut(BaseModel):
    username: str
    display_name: str
    role: str
    has_signature: bool
    file_size_kb: float | None = None
    uploaded_at: str | None = None


@router.get("", response_model=list[SignatureOut])
async def list_signatures(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """列出所有用户的电子签名状态"""
    result = await db.execute(
        text("""
            SELECT u.username, u.display_name, u.role,
                   s.source_file, s.uploaded_at
            FROM users u
            LEFT JOIN signatures s ON u.username = s.username
            ORDER BY u.role, u.username
        """)
    )
    out = []
    for r in result.fetchall():
        sig_file = r[3]
        has_sig = sig_file is not None
        sig_size = None
        if sig_file and os.path.isfile(sig_file):
            sig_size = round(os.path.getsize(sig_file) / 1024, 1)
        out.append(SignatureOut(
            username=r[0],
            display_name=r[1],
            role=r[2],
            has_signature=has_sig,
            file_size_kb=sig_size,
            uploaded_at=str(r[4]) if r[4] else None,
        ))
    return out


@router.post("/upload")
async def upload_signature(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
    target_username: str = Form(..., description="目标用户名"),
):
    """上传电子签名图片（管理员可替任意用户上传）"""
    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未选择文件")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 PNG/JPG 格式")

    # 验证用户存在
    user = await db.execute(
        text("SELECT 1 FROM users WHERE username=:u"), {"u": target_username}
    )
    if not user.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 确保签名目录存在
    sig_dir = Path(settings.SIGNATURE_DIR)
    sig_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件
    content = await file.read()
    filename = f"{target_username}{ext}"
    file_path = sig_dir / filename
    file_path.write_bytes(content)
    file_size = len(content)

    # 计算 SHA256
    sha = hashlib.sha256(content).hexdigest()

    # 更新数据库
    await db.execute(
        text("""
            INSERT INTO signatures (username, file_path, sha256, file_size, uploaded_at, uploaded_by)
            VALUES (:u, :fp, :sha, :fs, localtimestamp, :ub)
            ON CONFLICT (username) DO UPDATE SET
                file_path = :fp2, sha256 = :sha2, file_size = :fs2,
                uploaded_at = localtimestamp, uploaded_by = :ub2
        """),
        {
            "u": target_username, "fp": str(file_path), "sha": sha, "fs": file_size,
            "ub": current_user["username"],
            "fp2": str(file_path), "sha2": sha, "fs2": file_size, "ub2": current_user["username"],
        },
    )

    # 审计日志
    await log_operation(db, "signature", target_username, current_user, "上传签名")

    return {
        "message": f"签名已上传（{target_username}）",
        "username": target_username,
        "file_size_kb": round(file_size / 1024, 1),
        "sha256": sha[:16] + "...",
    }


@router.get("/{username}.png")
async def get_signature_image(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """获取用户的签名图片（可用作 <img src>）"""
    result = await db.execute(
        text("SELECT file_path FROM signatures WHERE username=:u"), {"u": username.replace(".png", "")}
    )
    row = result.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该用户未上传签名")

    file_path = row[0]
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="签名文件已丢失")

    return FileResponse(
        path=file_path,
        media_type="image/png",
    )


@router.delete("/{username}")
async def delete_signature(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """删除用户电子签名（管理员）"""
    result = await db.execute(
        text("SELECT file_path FROM signatures WHERE username=:u"), {"u": username}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该用户未上传签名")

    # 删除文件
    if row[0] and os.path.isfile(row[0]):
        os.remove(row[0])

    # 删除数据库记录
    await db.execute(text("DELETE FROM signatures WHERE username=:u"), {"u": username})

    # 审计日志
    await log_operation(db, "signature", username, current_user, "删除签名")

    return {"message": f"已删除 {username} 的电子签名"}
