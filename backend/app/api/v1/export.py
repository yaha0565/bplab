"""实验数据导出 Word API"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user, get_db

router = APIRouter(prefix="/export", tags=["数据导出"])


@router.get("/record/{task_no}")
async def export_record(
    task_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """导出实验原始记录为 .docx 文件"""
    # 查询任务信息
    task_result = await db.execute(
        text("SELECT experiment, experiment_code FROM tasks WHERE task_no=:t"),
        {"t": task_no},
    )
    task = task_result.fetchone()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # 查询最新记录
    rec_result = await db.execute(
        text("SELECT payload, version FROM records WHERE task_no=:t ORDER BY version DESC LIMIT 1"),
        {"t": task_no},
    )
    record = rec_result.fetchone()
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该任务无实验记录")

    experiment_code = task[1] or ""
    # 确定模板文件名
    from app.core.encoding_rules import template_code_for_kind, KIND_TO_TEMPLATE
    # experiment_code is like "I001", need to find kind
    # Look up kind from experiment_methods
    kind_result = await db.execute(
        text("SELECT kind FROM experiment_methods WHERE experiment_code=:c"),
        {"c": experiment_code},
    )
    kind_row = kind_result.fetchone()
    kind = kind_row[0] if kind_row else "generic"
    template_code = template_code_for_kind(kind)
    template_filename = f"RECORD_{template_code}.docx"

    from pathlib import Path
    template_path = Path(settings.TEMPLATE_DIR) / template_filename

    if not template_path.exists():
        # 无对应模板时返回记录 JSON
        import json
        output_path = Path(settings.UPLOAD_DIR) / f"{task_no}_record_v{record[1]}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(record[0] if isinstance(record[0], str) else json.dumps(record[0], ensure_ascii=False, default=str), encoding="utf-8")
        return FileResponse(
            path=str(output_path),
            filename=f"{task_no}_记录_v{record[1]}.json",
            media_type="application/json",
        )

    # 尝试使用模板引擎导出
    try:
        import json
        payload = json.loads(record[0]) if isinstance(record[0], str) else record[0]

        from docx import Document
        doc = Document(str(template_path))

        # 简单填充：替换占位符
        from docx_preview import docx_review_html
        # 这里需要实际的模板字段映射 — 对于 MVP，返回模板 + JSON 数据的组合
        # 将数据附加到模板末尾
        doc.add_page_break()
        doc.add_heading("实验数据", level=2)
        if isinstance(payload, dict):
            params = payload.get("parameters", {})
            rows = payload.get("rows", [])
            if params:
                doc.add_heading("实验参数", level=3)
                for key, value in params.items():
                    doc.add_paragraph(f"{key}: {value}")
            if rows:
                doc.add_heading("测量数据", level=3)
                for i, row in enumerate(rows):
                    doc.add_paragraph(f"试样 {i+1}: {row}")

        output_path = Path(settings.UPLOAD_DIR) / f"{task_no}_记录_v{record[1]}.docx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))

        return FileResponse(
            path=str(output_path),
            filename=f"{task_no}_实验记录_v{record[1]}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"导出失败: {e}")


@router.get("/report/{report_no}")
async def export_report(
    report_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """导出检验报告为 .docx 文件"""
    rep_result = await db.execute(
        text("SELECT status, commission_no, task_no, experiment, tester, verifier FROM reports WHERE report_no=:r"),
        {"r": report_no},
    )
    rep = rep_result.fetchone()
    if not rep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
    if rep[0] != "已发布":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅可导出已签发的报告")

    from pathlib import Path
    template_path = Path(settings.TEMPLATE_DIR) / "FORM_REPORT.docx"

    if not template_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告模板不存在")

    try:
        from docx import Document
        doc = Document(str(template_path))

        # 简单填充报告信息
        for para in doc.paragraphs:
            if "{{REPORT_NO}}" in para.text:
                para.text = para.text.replace("{{REPORT_NO}}", report_no)
            if "{{COMMISSION_NO}}" in para.text:
                para.text = para.text.replace("{{COMMISSION_NO}}", rep[1] or "")

        output_path = Path(settings.UPLOAD_DIR) / f"{report_no}.docx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))

        return FileResponse(
            path=str(output_path),
            filename=f"{report_no}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"导出失败: {e}")


class BatchExportRequest(BaseModel):
    task_nos: list[str] = []
    report_nos: list[str] = []


@router.post("/batch")
async def batch_export(
    body: BatchExportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """批量导出 — 将选中的任务记录和报告打包为 ZIP 下载"""
    if not body.task_nos and not body.report_nos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择要导出的任务或报告")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for tno in body.task_nos:
            try:
                rec_result = await db.execute(
                    text("SELECT payload, version FROM records WHERE task_no=:t ORDER BY version DESC LIMIT 1"),
                    {"t": tno},
                )
                record = rec_result.fetchone()
                if record:
                    import json
                    payload = json.loads(record[0]) if isinstance(record[0], str) else record[0]
                    zf.writestr(f"{tno}_记录_v{record[1]}.json",
                                json.dumps(payload, ensure_ascii=False, indent=2, default=str))
            except Exception:
                zf.writestr(f"{tno}_error.txt", f"导出 {tno} 时出错")

        for rno in body.report_nos:
            try:
                rep_result = await db.execute(
                    text("SELECT * FROM reports WHERE report_no=:r"),
                    {"r": rno},
                )
                rep = rep_result.fetchone()
                if rep:
                    rep_dict = dict(zip(rep_result.keys(), rep))
                    import json
                    zf.writestr(f"{rno}_报告.json",
                                json.dumps(rep_dict, ensure_ascii=False, indent=2, default=str))
            except Exception:
                zf.writestr(f"{rno}_error.txt", f"导出 {rno} 时出错")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=batch_export.zip"},
    )


@router.get("/commission/{commission_no}/items")
async def list_exportable_items(
    commission_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """列出委托下所有可导出的任务和报告"""
    task_result = await db.execute(
        text("""
            SELECT t.task_no, t.experiment, t.status, t.tester, t.package_no
            FROM tasks t
            JOIN sample_groups sg ON t.group_no = sg.group_no
            WHERE sg.commission_no = :c
            ORDER BY t.task_no
        """),
        {"c": commission_no},
    )
    tasks = [dict(zip(task_result.keys(), r)) for r in task_result.fetchall()]

    rep_result = await db.execute(
        text("""
            SELECT report_no, status, task_no, experiment, tester
            FROM reports WHERE commission_no = :c
            ORDER BY report_no
        """),
        {"c": commission_no},
    )
    reports = [dict(zip(rep_result.keys(), r)) for r in rep_result.fetchall()]

    return {"commission_no": commission_no, "tasks": tasks, "reports": reports}
