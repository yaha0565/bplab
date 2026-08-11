"""模板管理 API — 浏览/下载/预览 .docx 模板文件"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/templates", tags=["模板管理"])


class TemplateInfo(BaseModel):
    filename: str
    category: str  # RECORD / SOP / FORM
    display_name: str
    size_kb: float
    experiment_code: str | None = None  # 关联的实验编码 (R001-R015)


# 模板分类与显示名映射
TEMPLATE_CATEGORIES = {
    "RECORD": "实验原始记录模板",
    "SOP": "标准操作规程 (SOP)",
    "FORM": "管理表单模板",
}

# 记录模板 → 实验名称
RECORD_NAMES = {
    "R001": "表面粗糙度试验",
    "R004": "金属-陶瓷结合裂纹萌生试验",
    "R005": "金属内部质量X射线灰度分析",
    "R006": "翘曲变形试验",
    "R007": "热膨胀系数试验",
    "R009": "陶瓷牙耐急冷急热试验",
    "R010": "弯曲性能试验",
    "R011": "维氏硬度试验",
    "R012": "牙科材料色稳定性试验",
    "R013": "增材制造金属试样厚度测量",
    "R014": "定制式固定义齿综合检验",
    "R015": "定制式活动义齿综合检验",
}

FORM_NAMES = {
    "COMMISSION": "委托单",
    "HAZARDOUS_WASTE": "危废处置登记表",
    "REPORT": "检验报告",
    "REPORT_DELIVERY": "报告发放登记单",
    "SAMPLE_LOAN_RETURN": "样品借出/归还登记",
    "SAMPLE_REGISTER": "样品登记表",
}


def _parse_template_filename(filename: str) -> dict:
    """从文件名解析模板信息。"""
    import re
    name = filename.replace(".docx", "")
    # 新格式: Rxxx_实验名称_CMA原始记录表
    m = re.match(r'(R\d{3})_(.+?)(?:_CMA原始记录表)?$', name)
    if m:
        code = m.group(1)
        exp_name = m.group(2)
        return {"category": "RECORD", "display_name": f"{code} — {exp_name}", "experiment_code": code}
    # 旧格式: RECORD_R001_xxx / SOP_R001_xxx
    if name.startswith("RECORD_"):
        code = name.replace("RECORD_", "")
        exp_name = RECORD_NAMES.get(code, code)
        return {"category": "RECORD", "display_name": f"{code} — {exp_name}", "experiment_code": code}
    elif name.startswith("SOP_"):
        code = name.replace("SOP_", "")
        exp_name = RECORD_NAMES.get(code, code)
        return {"category": "SOP", "display_name": f"{code} — {exp_name} (SOP)", "experiment_code": code}
    elif name.startswith("FORM_"):
        form_key = name.replace("FORM_", "")
        form_name = FORM_NAMES.get(form_key, form_key)
        return {"category": "FORM", "display_name": f"{form_name} ({form_key})", "experiment_code": None}
    return {"category": "OTHER", "display_name": name, "experiment_code": None}


@router.get("", response_model=list[TemplateInfo])
async def list_templates(
    _user: Annotated[dict, Depends(get_current_user)],
    category: str | None = Query(None, description="RECORD / SOP / FORM"),
):
    """列出所有模板文件（按类别分组）"""
    template_dir = Path(settings.TEMPLATE_DIR)
    if not template_dir.exists():
        return []

    templates = []
    for f in sorted(template_dir.iterdir()):
        if not f.is_file() or not f.suffix == ".docx":
            continue
        info = _parse_template_filename(f.name)
        if category and info["category"] != category:
            continue
        size_kb = round(f.stat().st_size / 1024, 1)
        templates.append(TemplateInfo(
            filename=f.name,
            category=info["category"],
            display_name=info["display_name"],
            size_kb=size_kb,
            experiment_code=info["experiment_code"],
        ))

    return templates


@router.get("/versions")
async def list_template_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    experiment_code: str | None = Query(None, description="按实验编码过滤"),
):
    """获取模板版本列表（可按实验编码过滤）"""
    where = ""
    params: dict = {}
    if experiment_code:
        where = "WHERE experiment_code=:ec"
        params["ec"] = experiment_code

    result = await db.execute(
        text(f"SELECT experiment_code, doc_type, file_name, version, effective_date, status, created_at "
             f"FROM template_versions {where} ORDER BY experiment_code, doc_type"),
        params,
    )
    return [
        {
            "experiment_code": r[0], "doc_type": r[1], "file_name": r[2],
            "version": r[3], "effective_date": str(r[4]) if r[4] else None,
            "status": r[5], "created_at": str(r[6]) if r[6] else None,
        }
        for r in result.fetchall()
    ]


@router.get("/{filename}")
async def download_template(
    filename: str,
    _user: Annotated[dict, Depends(get_current_user)],
):
    """下载模板文件"""
    file_path = Path(settings.TEMPLATE_DIR) / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板文件不存在")
    if not filename.endswith(".docx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .docx 文件")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/{filename}/preview", response_class=HTMLResponse)
async def preview_template_html(
    filename: str,
    _user: Annotated[dict, Depends(get_current_user)],
):
    """预览模板 — 返回 HTML 渲染视图"""
    file_path = Path(settings.TEMPLATE_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板文件不存在")

    try:
        from app.services.docx_preview import docx_review_html
        content = file_path.read_bytes()
        html = docx_review_html(content, filename)
        return HTMLResponse(content=html)
    except ImportError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=f"预览功能不可用: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"预览生成失败: {e}")


# ── 模板上传 / 删除 / 重命名（管理员）──

@router.post("/upload")
async def upload_template(
    file: Annotated[UploadFile, File(...)],
    _user: Annotated[dict, Depends(require_role("管理员"))],
    display_name: str | None = Form(None, description="显示名称（可选）"),
):
    """上传新模板文件（管理员）"""
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 .docx 格式的模板文件",
        )

    template_dir = Path(settings.TEMPLATE_DIR)
    template_dir.mkdir(parents=True, exist_ok=True)

    # 用原始文件名；如已存在则拒绝
    dest = template_dir / file.filename
    if dest.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"模板文件 {file.filename} 已存在，请使用其他文件名或先删除旧版本",
        )

    content = await file.read()
    dest.write_bytes(content)

    info = _parse_template_filename(file.filename)
    return {
        "message": f"模板 {file.filename} 上传成功",
        "filename": file.filename,
        "category": info["category"],
        "display_name": info.get("display_name", display_name or file.filename),
        "size_kb": round(len(content) / 1024, 1),
    }


@router.delete("/{filename}")
async def delete_template(
    filename: str,
    _user: Annotated[dict, Depends(require_role("管理员"))],
):
    """删除模板文件（管理员）"""
    file_path = Path(settings.TEMPLATE_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板文件不存在")
    if not filename.endswith(".docx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .docx 文件")

    file_path.unlink()
    return {"message": f"模板 {filename} 已删除"}


class RenameTemplateRequest(BaseModel):
    new_filename: str


@router.put("/{filename}/rename")
async def rename_template(
    filename: str,
    body: RenameTemplateRequest,
    _user: Annotated[dict, Depends(require_role("管理员"))],
):
    """重命名模板文件（管理员）"""
    if not body.new_filename.endswith(".docx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名必须以 .docx 结尾")

    old_path = Path(settings.TEMPLATE_DIR) / filename
    if not old_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板文件不存在")

    new_path = Path(settings.TEMPLATE_DIR) / body.new_filename
    if new_path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="目标文件名已存在")

    old_path.rename(new_path)
    info = _parse_template_filename(body.new_filename)
    return {
        "message": f"已重命名为 {body.new_filename}",
        "old_filename": filename,
        "new_filename": body.new_filename,
        "category": info["category"],
        "display_name": info["display_name"],
    }
