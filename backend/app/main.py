"""BPLab Trace LIMS V11 — FastAPI 主入口"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    from pathlib import Path
    for d in [settings.UPLOAD_DIR, settings.ATTACHMENT_DIR, settings.SIGNATURE_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # 首次启动自动填充基础数据（实验方法、配置版本等）
    try:
        from app.core.seed import auto_seed
        result = await auto_seed()
        if any(v > 0 for v in result.values()):
            import logging
            logging.getLogger(__name__).info(
                f"Auto-seed 完成: methods={result['methods']}, "
                f"configs={result['configs']}, equipment={result['equipment']}, "
                f"bindings={result['bindings']}"
            )
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Auto-seed 跳过（数据库可能尚未就绪）")

    yield
    # 关闭时清理连接池
    from app.database import engine
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — 前端开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
