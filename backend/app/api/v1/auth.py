"""鉴权 API：登录 / 登出 / 当前用户"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["认证"])

# 从 constants.py 同步的菜单配置
ROLE_MENUS = {
    "管理员": [
        "首页看板", "单位信息库", "检测项目与方法库", "样品资料库",
        "委托与样品管理", "新建委托与入库", "任务包分配",
        "附件与内部追溯", "一键下载", "单据中心", "报告中心",
        "客户异议", "报告发放管理", "设备故障处置",
        "SOP与模板版本", "实验配置版本", "设备库", "用户与权限",
        "审计追踪", "通知中心", "样品借出与归还", "危废处理登记", "回库确认",
        "电子签名", "修改中心", "系统初始化",
    ],
    "样品管理员": [
        "首页看板", "单位信息库", "检测项目与方法库", "样品资料库", "设备库",
        "新建委托与入库", "委托与样品管理", "任务包分配", "回库确认",
        "附件与内部追溯", "一键下载", "单据中心", "报告发放管理", "客户异议",
        "设备故障处置", "通知中心",
    ],
    "实验员": [
        "首页看板", "我的任务包", "实验记录", "样品借出与归还",
        "危废处理登记", "设备故障处置", "附件与内部追溯", "一键下载", "单据中心",
        "通知中心",
    ],
    "复核员": [
        "首页看板", "原始记录复核", "设备故障处置", "附件与内部追溯",
        "一键下载", "单据中心", "通知中心",
    ],
    "质量负责人": [
        "首页看板", "报告中心", "客户异议", "设备故障处置", "附件与内部追溯",
        "一键下载", "单据中心", "通知中心", "审计追踪",
    ],
}


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    """用户登录，返回 JWT token"""
    result = await db.execute(
        text("SELECT username, display_name, role, password_hash, enabled FROM users WHERE username=:u AND enabled IS TRUE"),
        {"u": body.username},
    )
    row = result.fetchone()
    if not row or not verify_password(body.password, row[3]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = create_access_token(data={"sub": row[0], "role": row[2]})
    return LoginResponse(
        access_token=token,
        username=row[0],
        display_name=row[1],
        role=row[2],
        menus=ROLE_MENUS.get(row[2], []),
    )


@router.get("/me", response_model=UserInfo)
async def me(user: Annotated[dict, Depends(get_current_user)]):
    """获取当前登录用户信息"""
    return UserInfo(
        username=user["username"],
        display_name=user["display_name"],
        role=user["role"],
        enabled=user.get("enabled", True),
    )
