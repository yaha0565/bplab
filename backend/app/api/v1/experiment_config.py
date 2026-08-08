"""实验配置版本管理 API

保持实验过程可定制 — DB驱动的配置系统:
  1. 硬编码默认值 (experiment_schemas.py) — 安全网
  2. 数据库驱动配置 (experiment_config_versions + 6个配置子表) — 运行时权威来源
  3. 任务级快照 (task_config_snapshots) — 审计追溯
"""
from __future__ import annotations

import json
import os
import sys
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role

# ── 硬编码 schema 回退 ──
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from experiment_schemas import SCHEMAS

router = APIRouter(prefix="/config", tags=["实验配置"])


# ── 配置列表与详情 ──

@router.get("/methods")
async def list_experiment_methods(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """列出所有检测项目（含当前配置版本信息）"""
    result = await db.execute(
        text("""
            SELECT em.experiment_code, em.experiment_name, em.method_code, em.standard,
                   em.category, em.kind, em.enabled,
                   (SELECT ecv.version FROM experiment_config_versions ecv
                    WHERE ecv.experiment_code = em.experiment_code AND ecv.status = '现行'
                    LIMIT 1) AS current_version
            FROM experiment_methods em
            WHERE em.enabled = TRUE
            ORDER BY em.sort_order, em.experiment_code
        """)
    )
    return [
        {
            "experiment_code": r[0], "experiment_name": r[1], "method_code": r[2],
            "standard": r[3], "category": r[4], "kind": r[5], "enabled": r[6],
            "current_version": r[7],
        }
        for r in result.fetchall()
    ]


def _normalize_db_fields(db_fields: list[dict]) -> list[dict]:
    """将 DB 列名映射为前端期望的简写格式"""
    out = []
    for f in db_fields:
        out.append({
            "key": f.get("field_key", ""),
            "label": f.get("field_label", ""),
            "type": f.get("field_type", "text"),
            "default": _parse_default(f.get("field_default")),
            "options": _parse_options(f.get("field_options")),
            "readonly": bool(f.get("is_readonly")),
            "section_title": f.get("section_title", ""),
            "section_order": f.get("section_order", 0),
        })
    return out


def _normalize_db_columns(db_cols: list[dict]) -> list[dict]:
    out = []
    for c in db_cols:
        out.append({
            "column_key": c.get("column_key", ""),
            "column_label": c.get("column_label", ""),
            "column_type": c.get("column_type", "number"),
            "column_default": _parse_default(c.get("column_default")),
        })
    return out


def _normalize_db_photos(db_photos: list[dict]) -> list[dict]:
    return [{
        "code": p.get("checkpoint_code", ""),
        "label": p.get("checkpoint_label", ""),
    } for p in db_photos]


def _normalize_db_prechecks(db_prechecks: list[dict]) -> list[dict]:
    return [{
        "label": p.get("precheck_label", p.get("check_name", "")),
    } for p in db_prechecks]


def _parse_default(val):
    """将字符串默认值转为合适的 Python 类型"""
    if val is None or val == "":
        return ""
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    # 数字
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass
    # JSON array
    if s.startswith("[") and s.endswith("]"):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            pass
    return s


def _parse_options(val):
    """将 DB 中存储的 options 字符串转为列表"""
    if val is None or val == "":
        return []
    if isinstance(val, list):
        return val
    s = str(val).strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            pass
    # 分号或逗号分隔
    if ";" in s:
        return [x.strip() for x in s.split(";")]
    if "," in s:
        return [x.strip() for x in s.split(",")]
    return [s]


# ── 硬编码拍照节点（对齐 constants.py）──

_COMMON_PHOTO_CHECKPOINTS = [
    {"code": "ENV", "label": "实验开始温湿度表", "required": True},
    {"code": "SAMPLE_BEFORE", "label": "实验前样品及标签", "required": True},
    {"code": "DEVICE", "label": "设备编号/铭牌", "required": True},
    {"code": "PARAMETERS", "label": "设备参数或软件数据界面", "required": True},
    {"code": "SETUP", "label": "样品安装、装夹或放置状态", "required": True},
    {"code": "RESULT", "label": "最终读数、曲线或结果界面", "required": True},
    {"code": "SAMPLE_AFTER", "label": "实验结束后样品状态", "required": True},
    {"code": "REPORT_PHOTO", "label": "检验报告照片区域用代表性照片", "required": True},
]

# kind → 实验中文名映射
_KIND_TO_NAME = {
    "rough": "表面粗糙度试验",
    "mc_crack": "金属-陶瓷结合裂纹萌生试验",
    "xray": "金属内部质量X射线灰度分析",
    "warp": "翘曲变形试验",
    "cte": "热膨胀系数试验",
    "shock": "陶瓷牙耐急冷急热试验",
    "bend": "弯曲性能试验",
    "hv": "维氏硬度试验",
    "thickness": "增材制造金属试样厚度测量",
    "color": "牙科材料色稳定性试验",
    "fixed_denture": "定制式固定义齿综合检验",
    "removable_denture": "定制式活动义齿综合检验",
}

# 实验名 → 专属拍照节点（对齐 constants.py EXPERIMENT_PHOTO_CHECKPOINTS）
_EXPERIMENT_PHOTO_CHECKPOINTS = {
    "表面粗糙度试验": [
        {"code": "REFERENCE_CHECK", "label": "标准样块核查读数", "required": True},
        {"code": "SAMPLE_BEFORE", "label": "实验前样品标签", "required": True},
        {"code": "PROFILE", "label": "最终读数、轮廓曲线与结果界面", "required": True},
        {"code": "ROUGH_PARAMETERS", "label": "设备参数与软件数据界面", "required": True},
    ],
    "金属-陶瓷结合裂纹萌生试验": [
        {"code": "SAMPLE_BEFORE", "label": "实验前试样及标签", "required": True},
        {"code": "SPAN_FIXTURE", "label": "金瓷结合试验夹具和跨距", "required": True},
        {"code": "K_FACTOR", "label": "K值确定依据", "required": True},
        {"code": "FASTTEST_RESULT", "label": "FastTest的Ffail、k和τb结果界面", "required": True},
        {"code": "CRACK", "label": "裂纹萌生或陶瓷剥离状态", "required": True},
    ],
    "金属内部质量X射线灰度分析": [
        {"code": "IQI_POSITION", "label": "样品与孔形像质计摆放", "required": True},
        {"code": "EXPOSURE", "label": "曝光参数界面", "required": True},
        {"code": "RADIOGRAPH", "label": "原始X射线成像画面", "required": True},
        {"code": "ROI", "label": "ROI位置及灰度值", "required": True},
    ],
    "翘曲变形试验": [
        {"code": "H1", "label": "切割前H1测量界面", "required": True},
        {"code": "CUTTING", "label": "切割装夹和切割后状态", "required": True},
        {"code": "H2", "label": "切割后H2测量界面", "required": True},
    ],
    "热膨胀系数试验": [
        {"code": "CTE_PARAMETERS", "label": "设备参数或软件数据界面", "required": True},
    ],
    "陶瓷牙耐急冷急热试验": [
        {"code": "OVEN_TEMP", "label": "烘箱100±2℃实测温度", "required": True},
        {"code": "ICE_TEMP_START", "label": "试验前冰水1±1℃温度", "required": True},
        {"code": "ICE_TEMP_PROCESS", "label": "试验中每15分钟冰水复测读数", "required": True},
        {"code": "FIRST_HEAT", "label": "第一次加热开始/结束时间与温度", "required": True},
        {"code": "TRANSFER_COLD", "label": "急冷转移、浸没状态与时间", "required": True},
        {"code": "SECOND_HEAT", "label": "第二次加热时间与温度", "required": True},
        {"code": "COOL_TEMP", "label": "自然冷却后样品表面23±2℃", "required": True},
        {"code": "INSPECTION_LIGHT", "label": "外观检查光照度≥1000 lx", "required": True},
        {"code": "DAMAGE", "label": "逐颗裂纹、崩瓷或破损检查结果", "required": True},
    ],
    "弯曲性能试验": [
        {"code": "SENSOR_FACTOR", "label": "传感器校准系数和主机参数", "required": True},
        {"code": "SPAN_FIXTURE", "label": "夹具跨距和试样装夹", "required": True},
        {"code": "DEFLECTOMETER", "label": "挠度计接触与测量状态", "required": True},
        {"code": "ZERO_FORCE", "label": "清零后力值", "required": True},
        {"code": "FORCE_CURVE", "label": "力-位移曲线及Fmax", "required": True},
        {"code": "FRACTURE", "label": "断裂状态", "required": True},
    ],
    "维氏硬度试验": [
        {"code": "SAMPLE_BEFORE", "label": "实验前样品标签", "required": True},
        {"code": "HARDNESS_BLOCK", "label": "标准硬度块核查", "required": True},
        {"code": "INDENT", "label": "最终读数、曲线与结果界面", "required": True},
    ],
    "增材制造金属试样厚度测量": [
        {"code": "SAMPLE_BEFORE", "label": "实验前样品及标签", "required": True},
        {"code": "MEASURE_RESULT", "label": "各截面测量图像与实测值", "required": True},
        {"code": "FINAL_CURVE", "label": "最终读数、曲线与结果界面", "required": True},
    ],
    "牙科材料色稳定性试验": [
        {"code": "COVER", "label": "试样遮盖方式", "required": True},
        {"code": "WATER_LEVEL", "label": "试样安装和水位", "required": True},
        {"code": "START_DISPLAY", "label": "开始时温度、照度和时间", "required": True},
        {"code": "END_DISPLAY", "label": "结束时温度、照度和时间", "required": True},
        {"code": "D65_COMPARE", "label": "D65环境下色泽比较状态", "required": True},
        {"code": "OBSERVER_RESULT", "label": "三名观察者独立比较结果", "required": True},
    ],
    "定制式固定义齿综合检验": [
        {"code": "DESIGN_TRACE", "label": "设计单、模型及原材料追溯核查", "required": True},
        {"code": "FIXED_DENTURE_RESULT", "label": "表面、适合性、咬合及尺寸综合检验结果", "required": True},
        {"code": "MICRO_RESULT", "label": "粗糙度或孔隙度显微检查结果", "required": False},
    ],
    "定制式活动义齿综合检验": [
        {"code": "DESIGN_TRACE", "label": "设计单、模型及原材料追溯核查", "required": True},
        {"code": "REMOVABLE_DENTURE_RESULT", "label": "外形、适合性、厚度及咬合综合检验结果", "required": True},
        {"code": "XRAY_RESULT", "label": "金属内部质量X射线结果", "required": False},
        {"code": "COLOR_RESULT", "label": "色泽检查结果", "required": False},
    ],
}

# 简单回落使用通用拍照节点的实验 kind
_KINDS_WITH_SPECIFIC_PHOTOS = {"rough", "mc_crack", "hv", "thickness", "cte"}


def _get_photo_checkpoints(kind: str, experiment_name: str | None = None) -> list[dict]:
    """获取拍照节点：优先专属节点 → 通用节点"""
    # kind → 实验名 → 专属节点
    name = experiment_name or _KIND_TO_NAME.get(kind, "")
    specific = _EXPERIMENT_PHOTO_CHECKPOINTS.get(name, [])
    if specific and kind in _KINDS_WITH_SPECIFIC_PHOTOS:
        return specific
    return _COMMON_PHOTO_CHECKPOINTS + specific


def _build_fallback_config(experiment_code: str) -> dict | None:
    """从硬编码 SCHEMAS 构建前端可用配置（无 DB 版本时的安全网）"""
    schema = SCHEMAS.get(experiment_code)
    if not schema:
        return None

    fields = []
    for si, section in enumerate(schema.get("sections", [])):
        section_title = section.get("title", "")
        for fi, f in enumerate(section.get("fields", [])):
            fields.append({
                "key": f.get("key", ""),
                "label": f.get("label", ""),
                "type": f.get("type", "text"),
                "default": f.get("default", ""),
                "options": f.get("options", []),
                "readonly": f.get("readonly", False),
                "section_title": section_title,
                "section_order": si,
            })

    columns = []
    raw_columns = schema.get("columns", [])
    for i, col in enumerate(raw_columns):
        if isinstance(col, (list, tuple)) and len(col) >= 3:
            columns.append({
                "column_key": col[0],
                "column_label": col[1],
                "column_type": col[2],
                "column_default": "",
            })
        elif isinstance(col, dict):
            columns.append(col)

    kind = schema.get("kind", experiment_code)
    return {
        "experiment_code": experiment_code,
        "kind": kind,
        "fields": fields,
        "columns": columns,
        "photo_checkpoints": _get_photo_checkpoints(kind),
        "prechecks": schema.get("prechecks", []),
        "validation_rules": [],
        "equipment": [],
        "row_expansion": schema.get("row_expansion"),
        "face_labels": schema.get("face_labels"),
        "_source": "hardcoded",
    }


@router.get("/{experiment_code}")
async def get_current_config(
    experiment_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """获取某个实验的当前有效配置（含所有子组件）"""
    # 查当前生效版本
    config_result = await db.execute(
        text("""
            SELECT * FROM experiment_config_versions
            WHERE experiment_code = :ec AND status = '现行'
            ORDER BY effective_date DESC LIMIT 1
        """),
        {"ec": experiment_code},
    )
    config = config_result.fetchone()
    if not config:
        # ── 硬编码 schema 回退 ──
        fb = _build_fallback_config(experiment_code)
        if fb:
            return fb
        return {"experiment_code": experiment_code, "message": "无现行配置版本，使用硬编码默认值"}

    config_dict = dict(zip(config_result.keys(), config))
    config_id = config_dict["id"]

    # 查字段配置 → 标准化
    fields_result = await db.execute(
        text("SELECT * FROM experiment_config_fields WHERE config_id=:cid ORDER BY section_order, sort_order"),
        {"cid": config_id},
    )
    config_dict["fields"] = _normalize_db_fields(
        [dict(zip(fields_result.keys(), r)) for r in fields_result.fetchall()]
    )

    # 查测量列配置 → 标准化
    cols_result = await db.execute(
        text("SELECT * FROM experiment_config_columns WHERE config_id=:cid ORDER BY sort_order"),
        {"cid": config_id},
    )
    config_dict["columns"] = _normalize_db_columns(
        [dict(zip(cols_result.keys(), r)) for r in cols_result.fetchall()]
    )

    # 查拍照节点 → 标准化
    photos_result = await db.execute(
        text("SELECT * FROM experiment_config_photo_checkpoints WHERE config_id=:cid ORDER BY sort_order"),
        {"cid": config_id},
    )
    db_photos = [dict(zip(photos_result.keys(), r)) for r in photos_result.fetchall()]
    config_dict["photo_checkpoints"] = _normalize_db_photos(db_photos)

    # 查预检查项 → 标准化
    prechecks_result = await db.execute(
        text("SELECT * FROM experiment_config_prechecks WHERE config_id=:cid ORDER BY sort_order"),
        {"cid": config_id},
    )
    config_dict["prechecks"] = _normalize_db_prechecks(
        [dict(zip(prechecks_result.keys(), r)) for r in prechecks_result.fetchall()]
    )

    # 查验证规则
    rules_result = await db.execute(
        text("SELECT * FROM experiment_config_validation_rules WHERE config_id=:cid"),
        {"cid": config_id},
    )
    config_dict["validation_rules"] = [dict(zip(rules_result.keys(), r)) for r in rules_result.fetchall()]

    # 查设备绑定
    equip_result = await db.execute(
        text("""
            SELECT ece.*, er.equipment_name, er.model
            FROM experiment_config_equipment ece
            LEFT JOIN equipment_registry er ON ece.management_no = er.management_no
            WHERE ece.config_id = :cid
            ORDER BY ece.sort_order
        """),
        {"cid": config_id},
    )
    config_dict["equipment"] = [dict(zip(equip_result.keys(), r)) for r in equip_result.fetchall()]

    # ── DB 照片节点为空时回退到硬编码 ──
    if not config_dict.get("photo_checkpoints"):
        kind_row = await db.execute(
            text("SELECT kind FROM experiment_methods WHERE experiment_code=:ec"),
            {"ec": experiment_code},
        )
        kind = kind_row.fetchone()
        kind = kind[0] if kind else experiment_code
        config_dict["photo_checkpoints"] = _get_photo_checkpoints(kind)

    # ── DB 配置为空时回退到硬编码 schema ──
    if not config_dict.get("fields") and not config_dict.get("columns"):
        # 从 experiment_methods 查 kind
        kind_row = await db.execute(
            text("SELECT kind FROM experiment_methods WHERE experiment_code=:ec"),
            {"ec": experiment_code},
        )
        kind = kind_row.fetchone()
        kind = kind[0] if kind else experiment_code
        fb = _build_fallback_config(kind) or _build_fallback_config(experiment_code)
        if fb:
            fb["_source"] = "hardcoded-fallback"
            fb["experiment_code"] = experiment_code  # 保留原始 experiment_code
            return fb

    config_dict["_source"] = "database"
    return config_dict


@router.get("/{experiment_code}/versions/{version}")
async def get_config_version(
    experiment_code: str,
    version: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """获取指定版本的完整配置（含所有子组件）"""
    cfg = await db.execute(
        text("SELECT * FROM experiment_config_versions WHERE experiment_code=:ec AND version=:v"),
        {"ec": experiment_code, "v": version},
    )
    row = cfg.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置版本不存在")
    config_dict = dict(zip(cfg.keys(), row))
    config_id = config_dict["id"]

    # 加载所有子组件
    for table, normalizer, key in [
        ("experiment_config_fields", _normalize_db_fields, "fields"),
        ("experiment_config_columns", _normalize_db_columns, "columns"),
        ("experiment_config_photo_checkpoints", _normalize_db_photos, "photo_checkpoints"),
        ("experiment_config_prechecks", _normalize_db_prechecks, "prechecks"),
    ]:
        r = await db.execute(text(f"SELECT * FROM {table} WHERE config_id=:cid ORDER BY sort_order"), {"cid": config_id})
        config_dict[key] = normalizer([dict(zip(r.keys(), row)) for row in r.fetchall()])

    # 验证规则
    rules = await db.execute(text("SELECT * FROM experiment_config_validation_rules WHERE config_id=:cid"), {"cid": config_id})
    config_dict["validation_rules"] = [dict(zip(rules.keys(), r)) for r in rules.fetchall()]

    # 设备
    equip = await db.execute(
        text("SELECT ece.*, er.equipment_name, er.model FROM experiment_config_equipment ece LEFT JOIN equipment_registry er ON ece.management_no = er.management_no WHERE ece.config_id=:cid ORDER BY ece.sort_order"),
        {"cid": config_id},
    )
    config_dict["equipment"] = [dict(zip(equip.keys(), r)) for r in equip.fetchall()]

    # 空字段/列时回退硬编码模板
    if not config_dict.get("fields") and not config_dict.get("columns"):
        kind_row = await db.execute(text("SELECT kind FROM experiment_methods WHERE experiment_code=:ec"), {"ec": experiment_code})
        k = kind_row.fetchone()
        kind = k[0] if k else experiment_code
        fb = _build_fallback_config(kind) or _build_fallback_config(experiment_code)
        if fb:
            fb["_source"] = "hardcoded-template"
            fb["experiment_code"] = experiment_code
            fb["version"] = version
            return fb
    if not config_dict.get("photo_checkpoints"):
        kind_row = await db.execute(text("SELECT kind FROM experiment_methods WHERE experiment_code=:ec"), {"ec": experiment_code})
        k = kind_row.fetchone()
        kind = k[0] if k else experiment_code
        config_dict["photo_checkpoints"] = _get_photo_checkpoints(kind)

    config_dict["_source"] = "database"
    return config_dict


@router.get("/{experiment_code}/versions")
async def list_config_versions(
    experiment_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """列出某实验的所有配置版本"""
    result = await db.execute(
        text("""
            SELECT id, experiment_code, version, experiment_name, status,
                   effective_date, approved_by, approved_at, created_at
            FROM experiment_config_versions
            WHERE experiment_code = :ec
            ORDER BY created_at DESC
        """),
        {"ec": experiment_code},
    )
    return [dict(zip(result.keys(), r)) for r in result.fetchall()]


# ── 任务配置快照 ──

@router.get("/snapshot/{task_no}")
async def get_task_config_snapshot(
    task_no: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
):
    """获取任务的配置快照（审计追溯用）"""
    result = await db.execute(
        text("SELECT config_id, config_version, snapshot_json, snapshot_hash, created_at FROM task_config_snapshots WHERE task_no=:t"),
        {"t": task_no},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该任务无配置快照")
    return {
        "task_no": task_no,
        "config_id": row[0],
        "config_version": row[1],
        "snapshot": row[2],
        "snapshot_hash": row[3],
        "created_at": str(row[4]) if row[4] else None,
    }


# ── 配置版本 CRUD（管理员）──

class ConfigVersionCreate(BaseModel):
    experiment_code: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    experiment_name: str = Field(..., min_length=1)
    method_code: str = Field(..., min_length=1)
    standard: str | None = None
    category: str | None = None
    kind: str = "generic"
    default_location: str | None = None
    sop_version: str | None = None
    record_template_version: str | None = None
    software: str | None = None
    effective_date: str | None = None
    note: str | None = None
    # 子配置（可选，创建时一并写入）
    fields: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[dict[str, Any]] = Field(default_factory=list)
    photo_checkpoints: list[dict[str, Any]] = Field(default_factory=list)
    prechecks: list[dict[str, Any]] = Field(default_factory=list)
    validation_rules: list[dict[str, Any]] = Field(default_factory=list)
    equipment: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/{experiment_code}/versions", status_code=201)
async def create_config_version(
    experiment_code: str,
    body: ConfigVersionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """创建新的实验配置版本（管理员）"""
    # 验证 experiment_code 在 URL 和 body 中一致
    if body.experiment_code != experiment_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL 中的 experiment_code 与请求体不一致",
        )

    # 检查 experiment_code 是否存在于 experiment_methods
    method = await db.execute(
        text("SELECT 1 FROM experiment_methods WHERE experiment_code=:ec"),
        {"ec": experiment_code},
    )
    if not method.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"实验编码 {experiment_code} 不存在于方法库",
        )

    # 检查版本是否已存在
    existing = await db.execute(
        text("SELECT 1 FROM experiment_config_versions WHERE experiment_code=:ec AND version=:v"),
        {"ec": experiment_code, "v": body.version},
    )
    if existing.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"版本 {body.version} 已存在",
        )

    # 插入主配置
    result = await db.execute(
        text("""
            INSERT INTO experiment_config_versions
              (experiment_code, version, experiment_name, method_code, standard,
               category, kind, default_location, sop_version, record_template_version,
               software, status, effective_date, note, created_by)
            VALUES (:ec, :v, :en, :mc, :st, :cat, :kd, :dl, :sv, :rtv, :sw, '草稿', :ed, :nt, :cb)
            RETURNING id
        """),
        {
            "ec": experiment_code, "v": body.version, "en": body.experiment_name,
            "mc": body.method_code, "st": body.standard, "cat": body.category,
            "kd": body.kind, "dl": body.default_location, "sv": body.sop_version,
            "rtv": body.record_template_version, "sw": body.software,
            "ed": body.effective_date, "nt": body.note, "cb": current_user["username"],
        },
    )
    config_id = result.fetchone()[0]

    # 插入子配置
    _insert_config_children(db, config_id, body)

    return {
        "message": f"配置版本 {body.version} 创建成功",
        "config_id": config_id,
        "experiment_code": experiment_code,
        "version": body.version,
        "status": "草稿",
    }


class ConfigVersionUpdate(BaseModel):
    """更新配置版本（草稿状态下可修改）"""
    experiment_name: str | None = None
    method_code: str | None = None
    standard: str | None = None
    category: str | None = None
    kind: str | None = None
    default_location: str | None = None
    sop_version: str | None = None
    record_template_version: str | None = None
    software: str | None = None
    effective_date: str | None = None
    note: str | None = None
    fields: list[dict[str, Any]] | None = None
    columns: list[dict[str, Any]] | None = None
    photo_checkpoints: list[dict[str, Any]] | None = None
    prechecks: list[dict[str, Any]] | None = None
    validation_rules: list[dict[str, Any]] | None = None
    equipment: list[dict[str, Any]] | None = None


@router.put("/{experiment_code}/versions/{version}")
async def update_config_version(
    experiment_code: str,
    version: str,
    body: ConfigVersionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """更新实验配置版本（仅草稿状态可修改）"""
    # 查找配置
    cfg = await db.execute(
        text("SELECT id, status FROM experiment_config_versions WHERE experiment_code=:ec AND version=:v"),
        {"ec": experiment_code, "v": version},
    )
    row = cfg.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置版本不存在")

    config_id, current_status = row[0], row[1]
    if current_status != "草稿":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅草稿状态可修改，当前状态：{current_status}",
        )

    # 更新主配置中的非空字段
    updatable = {
        "experiment_name", "method_code", "standard", "category", "kind",
        "default_location", "sop_version", "record_template_version",
        "software", "effective_date", "note",
    }
    set_clauses = []
    params: dict[str, Any] = {"cid": config_id}
    for field_name in updatable:
        val = getattr(body, field_name, None)
        if val is not None:
            set_clauses.append(f"{field_name}=:{field_name}")
            params[field_name] = val
    if set_clauses:
        await db.execute(
            text(f"UPDATE experiment_config_versions SET {', '.join(set_clauses)} WHERE id=:cid"),
            params,
        )

    # 如果提供了子配置，先删后插
    if body.fields is not None:
        await db.execute(text("DELETE FROM experiment_config_fields WHERE config_id=:cid"), {"cid": config_id})
        _insert_fields(db, config_id, body.fields)
    if body.columns is not None:
        await db.execute(text("DELETE FROM experiment_config_columns WHERE config_id=:cid"), {"cid": config_id})
        _insert_columns(db, config_id, body.columns)
    if body.photo_checkpoints is not None:
        await db.execute(text("DELETE FROM experiment_config_photo_checkpoints WHERE config_id=:cid"), {"cid": config_id})
        _insert_photo_checkpoints(db, config_id, body.photo_checkpoints)
    if body.prechecks is not None:
        await db.execute(text("DELETE FROM experiment_config_prechecks WHERE config_id=:cid"), {"cid": config_id})
        _insert_prechecks(db, config_id, body.prechecks)
    if body.validation_rules is not None:
        await db.execute(text("DELETE FROM experiment_config_validation_rules WHERE config_id=:cid"), {"cid": config_id})
        _insert_validation_rules(db, config_id, body.validation_rules)
    if body.equipment is not None:
        await db.execute(text("DELETE FROM experiment_config_equipment WHERE config_id=:cid"), {"cid": config_id})
        _insert_equipment(db, config_id, body.equipment)

    return {"message": f"配置版本 {version} 已更新", "config_id": config_id}


class ActivateVersionRequest(BaseModel):
    status: str = Field(..., pattern=r"^(现行|历史)$")


@router.put("/{experiment_code}/versions/{version}/status")
async def set_config_version_status(
    experiment_code: str,
    version: str,
    body: ActivateVersionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """激活/归档配置版本（管理员）

    - 设为「现行」: 先将该实验所有现行版本归档为「历史」, 再将目标版本设为「现行」
    - 设为「历史」: 直接归档
    """
    cfg = await db.execute(
        text("SELECT id, status FROM experiment_config_versions WHERE experiment_code=:ec AND version=:v"),
        {"ec": experiment_code, "v": version},
    )
    row = cfg.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置版本不存在")

    config_id, current_status = row[0], row[1]

    if body.status == "现行":
        # 先将该实验所有现行版本归档
        await db.execute(
            text("""
                UPDATE experiment_config_versions
                SET status='历史', approved_by=:cb, approved_at=now()
                WHERE experiment_code=:ec AND status='现行'
            """),
            {"ec": experiment_code, "cb": current_user["username"]},
        )
        # 激活目标版本
        await db.execute(
            text("""
                UPDATE experiment_config_versions
                SET status='现行', effective_date=CURRENT_DATE, approved_by=:cb, approved_at=now()
                WHERE id=:cid
            """),
            {"cid": config_id, "cb": current_user["username"]},
        )
    else:
        # 归档
        await db.execute(
            text("UPDATE experiment_config_versions SET status='历史' WHERE id=:cid"),
            {"cid": config_id},
        )

    return {"message": f"配置版本 {version} 状态已更新为「{body.status}」"}


@router.delete("/{experiment_code}/versions/{version}")
async def delete_config_version(
    experiment_code: str,
    version: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role("管理员"))],
):
    """删除配置版本（仅草稿状态可删除，管理员）"""
    cfg = await db.execute(
        text("SELECT id, status FROM experiment_config_versions WHERE experiment_code=:ec AND version=:v"),
        {"ec": experiment_code, "v": version},
    )
    row = cfg.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置版本不存在")

    config_id, current_status = row[0], row[1]
    if current_status != "草稿":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅草稿状态可删除，当前状态：{current_status}",
        )

    # CASCADE 会删除子表记录
    await db.execute(text("DELETE FROM experiment_config_versions WHERE id=:cid"), {"cid": config_id})
    return {"message": f"配置版本 {version} 已删除"}


# ── 辅助函数 ──

def _insert_config_children(db: AsyncSession, config_id: int, body: ConfigVersionCreate) -> None:
    """批量插入子配置"""
    if body.fields:
        _insert_fields(db, config_id, body.fields)
    if body.columns:
        _insert_columns(db, config_id, body.columns)
    if body.photo_checkpoints:
        _insert_photo_checkpoints(db, config_id, body.photo_checkpoints)
    if body.prechecks:
        _insert_prechecks(db, config_id, body.prechecks)
    if body.validation_rules:
        _insert_validation_rules(db, config_id, body.validation_rules)
    if body.equipment:
        _insert_equipment(db, config_id, body.equipment)


def _insert_fields(db: AsyncSession, config_id: int, items: list[dict[str, Any]]) -> None:
    for i, f in enumerate(items):
        db.execute(
            text("""
                INSERT INTO experiment_config_fields
                  (config_id, section_title, section_order, field_key, field_label,
                   field_type, field_default, field_options, is_required, is_readonly, is_actual, sort_order)
                VALUES (:cid, :st, :so, :fk, :fl, :ft, :fd, :fo, :ir, :iro, :ia, :srt)
            """),
            {
                "cid": config_id, "st": f.get("section_title", ""),
                "so": f.get("section_order", 1), "fk": f.get("field_key", f"field_{i}"),
                "fl": f.get("field_label", f"字段 {i+1}"), "ft": f.get("field_type", "text"),
                "fd": str(f.get("field_default", "")), "fo": str(f.get("field_options", "")),
                "ir": f.get("is_required", False), "iro": f.get("is_readonly", False),
                "ia": f.get("is_actual", False), "srt": f.get("sort_order", i),
            },
        )


def _insert_columns(db: AsyncSession, config_id: int, items: list[dict[str, Any]]) -> None:
    for i, c in enumerate(items):
        db.execute(
            text("""
                INSERT INTO experiment_config_columns
                  (config_id, column_key, column_label, column_type, is_required,
                   column_default, calc_expression, calc_precision, sort_order)
                VALUES (:cid, :ck, :cl, :ct, :ir, :cd, :ce, :cp, :srt)
            """),
            {
                "cid": config_id, "ck": c.get("column_key", f"col_{i}"),
                "cl": c.get("column_label", f"列 {i+1}"), "ct": c.get("column_type", "number"),
                "ir": c.get("is_required", False), "cd": str(c.get("column_default", "")),
                "ce": c.get("calc_expression"), "cp": c.get("calc_precision", 3),
                "srt": c.get("sort_order", i),
            },
        )


def _insert_photo_checkpoints(db: AsyncSession, config_id: int, items: list[dict[str, Any]]) -> None:
    for i, p in enumerate(items):
        db.execute(
            text("""
                INSERT INTO experiment_config_photo_checkpoints
                  (config_id, checkpoint_code, checkpoint_label, is_required, is_sample_level, checkpoint_group, sort_order)
                VALUES (:cid, :cc, :cl, :ir, :isl, :cg, :srt)
            """),
            {
                "cid": config_id, "cc": p.get("checkpoint_code", f"photo_{i}"),
                "cl": p.get("checkpoint_label", f"拍照节点 {i+1}"),
                "ir": p.get("is_required", True), "isl": p.get("is_sample_level", False),
                "cg": p.get("checkpoint_group"), "srt": p.get("sort_order", i),
            },
        )


def _insert_prechecks(db: AsyncSession, config_id: int, items: list[dict[str, Any]]) -> None:
    for i, p in enumerate(items):
        db.execute(
            text("""
                INSERT INTO experiment_config_prechecks
                  (config_id, precheck_code, precheck_label, is_required, sort_order)
                VALUES (:cid, :pc, :pl, :ir, :srt)
            """),
            {
                "cid": config_id, "pc": p.get("precheck_code", f"precheck_{i}"),
                "pl": p.get("precheck_label", f"预检查项 {i+1}"),
                "ir": p.get("is_required", True), "srt": p.get("sort_order", i),
            },
        )


def _insert_validation_rules(db: AsyncSession, config_id: int, items: list[dict[str, Any]]) -> None:
    for r in items:
        db.execute(
            text("""
                INSERT INTO experiment_config_validation_rules
                  (config_id, rule_type, target_field, rule_value, error_message, is_row_level)
                VALUES (:cid, :rt, :tf, :rv, :em, :irl)
            """),
            {
                "cid": config_id, "rt": r.get("rule_type", "range"),
                "tf": r.get("target_field", ""), "rv": r.get("rule_value", ""),
                "em": r.get("error_message"), "irl": r.get("is_row_level", False),
            },
        )


def _insert_equipment(db: AsyncSession, config_id: int, items: list[dict[str, Any]]) -> None:
    for i, e in enumerate(items):
        db.execute(
            text("""
                INSERT INTO experiment_config_equipment
                  (config_id, management_no, binding_role, required, sort_order, note)
                VALUES (:cid, :mn, :br, :req, :srt, :nt)
            """),
            {
                "cid": config_id, "mn": e.get("management_no", ""),
                "br": e.get("binding_role", "primary"), "req": e.get("required", False),
                "srt": e.get("sort_order", i), "nt": e.get("note"),
            },
        )
