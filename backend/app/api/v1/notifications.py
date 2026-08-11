"""站内通知 API"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db

router = APIRouter(prefix="/notifications", tags=["通知"])


class MarkReadRequest(BaseModel):
    ids: list[int] | None = None  # None = 全部已读


@router.get("")
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """获取当前用户的未读通知"""
    result = await db.execute(
        text("SELECT * FROM notifications WHERE recipient=:u AND read_at IS NULL ORDER BY id DESC LIMIT 50"),
        {"u": user["username"]},
    )
    return [dict(zip(result.keys(), r)) for r in result.fetchall()]


@router.put("/read")
async def mark_read(
    body: MarkReadRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    """标记通知为已读"""
    if body.ids:
        await db.execute(
            text("UPDATE notifications SET read_at=localtimestamp WHERE recipient=:u AND id = ANY(:ids)"),
            {"u": user["username"], "ids": body.ids},
        )
    else:
        await db.execute(
            text("UPDATE notifications SET read_at=localtimestamp WHERE recipient=:u AND read_at IS NULL"),
            {"u": user["username"]},
        )
    return {"message": "已标记为已读"}
