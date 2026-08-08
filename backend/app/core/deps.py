"""FastAPI 依赖注入：当前用户 + 权限检查"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """从 JWT 解析当前用户，返回 {username, display_name, role}"""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")

    result = await db.execute(
        text("SELECT username, display_name, role, enabled FROM users WHERE username=:u AND enabled IS TRUE"),
        {"u": username},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    return {"username": row[0], "display_name": row[1], "role": row[2], "enabled": row[3]}


def require_role(*roles: str):
    """生成一个依赖：只允许指定角色访问"""

    async def checker(
        user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {'/'.join(roles)} 权限",
            )
        return user

    return checker
