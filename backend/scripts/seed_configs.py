"""一键填充 12 个实验的 DB 配置版本 (V2.0) —— 自包含、零依赖

数据与 experiment_schemas.py + experiment_config.py 硬编码常量严格一致。

用法:
  cd backend
  python scripts/seed_configs.py

前置条件:
  - PostgreSQL 已运行且 migrations/001_schema.sql 已执行
  - experiment_methods 表已有 I001-I012 记录
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date

# 确保 backend 在 sys.path 中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)

import asyncpg
from app.config import settings

# ═══════════════════════════════════════════════════════════════
# 12 个实验的元数据（与 reference EXPERIMENTS 一致）
# ═══════════════════════════════════════════════════════════════

EXPERIMENT_META: dict[str, dict] = {
    "I001": {"name": "表面粗糙度试验", "kind": "rough", "method": "YY/T 1702",
             "standard": "YY/T 1702-2020；GB/T 10610-2009", "category": "增材制造检测",
             "location": "显微检测室"},
    "I002": {"name": "金属-陶瓷结合裂纹萌生试验", "kind": "mc_crack", "method": "YY 0621.1",
             "standard": "YY 0621.1-2016 / ISO 9693-1", "category": "力学性能检测",
             "location": "性能检测室"},
    "I003": {"name": "金属内部质量X射线灰度分析", "kind": "xray", "method": "GB 17168",
             "standard": "GB 17168及实验室受控SOP", "category": "内部质量检测",
             "location": "无损检测室"},
    "I004": {"name": "翘曲变形试验", "kind": "warp", "method": "YY/T 1702",
             "standard": "YY/T 1702-2020 第7.3.2条", "category": "增材制造检测",
             "location": "显微检测室"},
    "I005": {"name": "热膨胀系数试验", "kind": "cte", "method": "YY 0621.1",
             "standard": "YY 0621.1及实验室受控SOP", "category": "物理性能检测",
             "location": "性能检测室"},
    "I006": {"name": "陶瓷牙耐急冷急热试验", "kind": "shock", "method": "YY 0300",
             "standard": "YY 0300-2009 第7.10条", "category": "陶瓷材料检测",
             "location": "性能检测室"},
    "I007": {"name": "弯曲性能试验", "kind": "bend", "method": "YY/T 1702",
             "standard": "YY/T 1702-2020", "category": "力学性能检测",
             "location": "性能检测室"},
    "I008": {"name": "维氏硬度试验", "kind": "hv", "method": "GB/T 4340.1",
             "standard": "GB/T 4340.1-2024", "category": "力学性能检测",
             "location": "显微检测室"},
    "I009": {"name": "增材制造金属试样厚度测量", "kind": "thickness", "method": "YY/T 1702",
             "standard": "YY/T 1702-2020", "category": "增材制造检测",
             "location": "显微检测室"},
    "I010": {"name": "牙科材料色稳定性试验", "kind": "color", "method": "YY 0710",
             "standard": "YY 0710及产品技术要求", "category": "物理性能检测",
             "location": "外观检测室"},
    "I011": {"name": "定制式固定义齿综合检验", "kind": "fixed_denture", "method": "YY/T 1936",
             "standard": "YY/T 1936及产品技术要求", "category": "定制式义齿",
             "location": "外观检测室"},
    "I012": {"name": "定制式活动义齿综合检验", "kind": "removable_denture", "method": "YY 0270.1",
             "standard": "YY 0270.1及产品技术要求", "category": "定制式义齿",
             "location": "外观检测室"},
}

SEED_VERSION = "V2.0"
SEED_NOTE = f"由 seed_configs.py 批量生成, 对齐 streamlit-legacy V9.4.2 ({date.today().isoformat()})"

# ═══════════════════════════════════════════════════════════════
# 在这里直接导入 schemas (避免循环依赖)
# ═══════════════════════════════════════════════════════════════
_parent_dir = os.path.dirname(_backend_dir)
sys.path.insert(0, _parent_dir)
from experiment_schemas import SCHEMAS, COMMON_PROCESS_OBSERVATIONS, SUPPLEMENTAL_PROCESS_FIELDS

# ═══════════════════════════════════════════════════════════════
# 从 experiment_config.py 内联的关键常量（避免导入整个模块）
# ═══════════════════════════════════════════════════════════════

# CMA 通用拍照节点（required=False）
_COMMON_PHOTO_CHECKPOINTS = [
    {"code": "ENV", "label": "实验开始温湿度表", "required": False, "is_sample_level": False, "checkpoint_group": "环境与设备"},
    {"code": "SAMPLE_BEFORE", "label": "实验前样品及标签", "required": False, "is_sample_level": False, "checkpoint_group": "样品状态"},
    {"code": "DEVICE", "label": "设备编号/铭牌", "required": False, "is_sample_level": False, "checkpoint_group": "环境与设备"},
    {"code": "PARAMETERS", "label": "设备参数或软件数据界面", "required": False, "is_sample_level": False, "checkpoint_group": "环境与设备"},
    {"code": "SETUP", "label": "样品安装、装夹或放置状态", "required": False, "is_sample_level": False, "checkpoint_group": "样品状态"},
    {"code": "RESULT", "label": "最终读数、曲线或结果界面", "required": False, "is_sample_level": False, "checkpoint_group": "结果界面"},
    {"code": "SAMPLE_AFTER", "label": "实验结束后样品状态", "required": False, "is_sample_level": False, "checkpoint_group": "样品状态"},
    {"code": "REPORT_PHOTO", "label": "检验报告照片区域用代表性照片", "required": False, "is_sample_level": False, "checkpoint_group": "报告归档"},
]

# 实验专属拍照节点（对齐 reference V9.4.2）
_EXPERIMENT_PHOTO_CHECKPOINTS = {
    "表面粗糙度试验": [
        {"code": "ROUGH_POINT_1", "label": "测量点①拍照", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "ROUGH_POINT_2", "label": "测量点②拍照", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "ROUGH_POINT_3", "label": "测量点③拍照", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "ROUGH_CURVE_RESULT", "label": "测量曲线、计算设置与结果界面", "required": True, "is_sample_level": False, "checkpoint_group": "结果界面"},
    ],
    "金属-陶瓷结合裂纹萌生试验": [
        {"code": "MC_K_VALUE", "label": "试样K值拍照", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "MC_REPORT", "label": "报告拍照", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
    ],
    "金属内部质量X射线灰度分析": [
        {"code": "IQI_POSITION", "label": "样品与孔形像质计摆放", "required": False, "is_sample_level": False, "checkpoint_group": "装夹与核查"},
        {"code": "EXPOSURE", "label": "曝光参数界面", "required": False, "is_sample_level": False, "checkpoint_group": "环境与设备"},
        {"code": "RADIOGRAPH", "label": "原始X射线成像画面", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "ROI", "label": "ROI位置及灰度值", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
    ],
    "翘曲变形试验": [
        {"code": "H1_BASELINE", "label": "切割前基准线到自由端中点距离", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "H2_BASELINE", "label": "切割后基准线到自由端中点距离", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "WARP_REPORT_1", "label": "试验报告拍照①", "required": True, "is_sample_level": False, "checkpoint_group": "结果界面"},
        {"code": "WARP_REPORT_2", "label": "试验报告拍照②", "required": True, "is_sample_level": False, "checkpoint_group": "结果界面"},
        {"code": "WARP_REPORT_3", "label": "试验报告拍照③", "required": True, "is_sample_level": False, "checkpoint_group": "结果界面"},
    ],
    "热膨胀系数试验": [
        {"code": "CTE_PARAM_SET", "label": "试验参数设定拍照", "required": True, "is_sample_level": False, "checkpoint_group": "环境与设备"},
        {"code": "CTE_REPORT", "label": "样品试验报告拍照", "required": True, "is_sample_level": False, "checkpoint_group": "结果界面"},
    ],
    "陶瓷牙耐急冷急热试验": [
        {"code": "SHOCK_BEFORE", "label": "试验前试样拍照", "required": True, "is_sample_level": True, "checkpoint_group": "样品状态"},
        {"code": "SHOCK_AFTER", "label": "试验后试样拍照", "required": True, "is_sample_level": True, "checkpoint_group": "样品状态"},
        {"code": "OVEN_TEMP", "label": "烘箱100±2℃实测温度", "required": False, "is_sample_level": False, "checkpoint_group": "环境与设备"},
        {"code": "ICE_TEMP_START", "label": "试验前冰水1±1℃温度", "required": False, "is_sample_level": False, "checkpoint_group": "环境与设备"},
        {"code": "ICE_TEMP_PROCESS", "label": "试验中每15分钟冰水复测读数", "required": False, "is_sample_level": False, "checkpoint_group": "环境与设备"},
        {"code": "FIRST_HEAT", "label": "第一次加热开始/结束时间与温度", "required": False, "is_sample_level": False, "checkpoint_group": "过程记录"},
        {"code": "TRANSFER_COLD", "label": "急冷转移、浸没状态与时间", "required": False, "is_sample_level": False, "checkpoint_group": "过程记录"},
        {"code": "SECOND_HEAT", "label": "第二次加热时间与温度", "required": False, "is_sample_level": False, "checkpoint_group": "过程记录"},
        {"code": "COOL_TEMP", "label": "自然冷却后样品表面23±2℃", "required": False, "is_sample_level": False, "checkpoint_group": "过程记录"},
        {"code": "INSPECTION_LIGHT", "label": "外观检查光照度≥1000 lx", "required": False, "is_sample_level": False, "checkpoint_group": "核查与设备"},
        {"code": "DAMAGE", "label": "逐颗裂纹、崩瓷或破损检查结果", "required": False, "is_sample_level": True, "checkpoint_group": "结果界面"},
    ],
    "弯曲性能试验": [
        {"code": "BEND_REPORT", "label": "报告拍照", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
    ],
    "维氏硬度试验": [
        {"code": "HV_LOAD_TIME", "label": "载荷和保荷时间", "required": True, "is_sample_level": False, "checkpoint_group": "环境与设备"},
        {"code": "HV_REPORT_1", "label": "报告拍照①", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "HV_REPORT_2", "label": "报告拍照②", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
    ],
    "增材制造金属试样厚度测量": [
        {"code": "FIXED_DIST_1", "label": "固定端距离拍照①", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "FIXED_DIST_2", "label": "固定端距离拍照②", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "FIXED_DIST_3", "label": "固定端距离拍照③", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "MID_DIST_1", "label": "中间距离拍照①", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "MID_DIST_2", "label": "中间距离拍照②", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "MID_DIST_3", "label": "中间距离拍照③", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "FREE_END_1", "label": "自由端拍照①", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "FREE_END_2", "label": "自由端拍照②", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "FREE_END_3", "label": "自由端拍照③", "required": True, "is_sample_level": True, "checkpoint_group": "测量点"},
        {"code": "THICK_REPORT", "label": "报告拍照", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
    ],
    "牙科材料色稳定性试验": [
        {"code": "COLOR_BEFORE", "label": "试验前试样拍照", "required": True, "is_sample_level": True, "checkpoint_group": "样品状态"},
        {"code": "COLOR_AFTER", "label": "试验后试样拍照", "required": True, "is_sample_level": True, "checkpoint_group": "样品状态"},
    ],
    "定制式固定义齿综合检验": [
        {"code": "DESIGN_TRACE", "label": "设计单、模型及原材料追溯核查", "required": True, "is_sample_level": False, "checkpoint_group": "装夹与核查"},
        {"code": "FIXED_DENTURE_RESULT", "label": "表面、适合性、咬合及尺寸综合检验结果", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "MICRO_RESULT", "label": "粗糙度或孔隙度显微检查结果", "required": False, "is_sample_level": False, "checkpoint_group": "结果界面"},
    ],
    "定制式活动义齿综合检验": [
        {"code": "DESIGN_TRACE", "label": "设计单、模型及原材料追溯核查", "required": True, "is_sample_level": False, "checkpoint_group": "装夹与核查"},
        {"code": "REMOVABLE_DENTURE_RESULT", "label": "外形、适合性、厚度及咬合综合检验结果", "required": True, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "XRAY_RESULT", "label": "金属内部质量X射线结果", "required": False, "is_sample_level": True, "checkpoint_group": "结果界面"},
        {"code": "COLOR_RESULT", "label": "色泽检查结果", "required": False, "is_sample_level": True, "checkpoint_group": "结果界面"},
    ],
}

# 精简模式：仅使用专属节点的实验 kind
_KINDS_ONLY_SPECIFIC_PHOTOS = {"rough", "mc_crack", "cte", "hv", "thickness", "bend"}


# ═══════════════════════════════════════════════════════════════
# 数据构建函数
# ═══════════════════════════════════════════════════════════════

def _build_fields(code: str) -> list[dict]:
    """从 SCHEMAS 提取字段列表"""
    kind = EXPERIMENT_META[code]["kind"]
    schema = SCHEMAS.get(kind)
    if not schema:
        return []
    result = []
    for si, section in enumerate(schema.get("sections", [])):
        title = section.get("title", "")
        for fi, f in enumerate(section.get("fields", [])):
            default_val = f.get("default")
            if default_val is None:
                default_str = ""
            elif isinstance(default_val, list):
                default_str = ",".join(str(v) for v in default_val)
            elif isinstance(default_val, bool):
                default_str = "true" if default_val else "false"
            else:
                default_str = str(default_val)
            result.append({
                "section_title": title,
                "section_order": si + 1,
                "field_key": f.get("key", ""),
                "field_label": f.get("label", ""),
                "field_type": f.get("type", "text"),
                "field_default": default_str,
                "field_options": ",".join(f.get("options", [])) if f.get("options") else "",
                "is_required": f.get("required", False),
                "is_readonly": f.get("readonly", False),
                "is_actual": f.get("actual", False),
                "sort_order": fi + 1,
            })
    return result


# Known defaults for measurement columns (aligned with reference _default_for_column)
_COLUMN_DEFAULTS = {
    ("rough", "limit"): 15.0,
    ("warp", "limit"): 0.5,
    ("bend", "length"): 25.0,
    ("bend", "width"): 2.0,
    ("bend", "height"): 2.0,
    ("bend", "span"): 20.0,
    ("bend", "speed"): 1.0,
    ("cte", "t1"): 25.0,
    ("cte", "t2"): 550.0,
}


def _build_columns(code: str) -> list[dict]:
    """从 SCHEMAS 提取测量列"""
    kind = EXPERIMENT_META[code]["kind"]
    schema = SCHEMAS.get(kind)
    if not schema:
        return []
    result = []
    for ci, col in enumerate(schema.get("columns", [])):
        if isinstance(col, (list, tuple)) and len(col) >= 2:
            col_type = col[2] if len(col) >= 3 else "text"
            # 解析 select:opts 格式
            if col_type.startswith("select:"):
                opts = col_type.split(":", 1)[1]
                col_type = "select"
            else:
                opts = ""
            # Resolve known numeric default
            num_default = _COLUMN_DEFAULTS.get((kind, col[0]))
            if num_default is not None:
                default_val = str(num_default)
            elif opts:
                default_val = opts  # select options string
            else:
                default_val = ""
            entry = {
                "column_key": col[0],
                "column_label": col[1],
                "column_type": col_type,
                "is_required": True,
                "column_default": default_val,
                "sort_order": ci + 1,
            }
            if col_type == "calc":
                entry["calc_expression"] = col[1]
                entry["calc_precision"] = 3
            else:
                entry["calc_expression"] = ""
                entry["calc_precision"] = 3
            result.append(entry)
    return result


def _build_photos(code: str) -> list[dict]:
    """获取拍照节点（对齐 reference photo_checkpoints()）"""
    kind = EXPERIMENT_META[code]["kind"]
    name = EXPERIMENT_META[code]["name"]

    specific = _EXPERIMENT_PHOTO_CHECKPOINTS.get(name, [])
    if kind in _KINDS_ONLY_SPECIFIC_PHOTOS and specific:
        checkpoints = list(specific)
    elif specific:
        checkpoints = list(_COMMON_PHOTO_CHECKPOINTS) + list(specific)
    else:
        checkpoints = list(_COMMON_PHOTO_CHECKPOINTS)

    result = []
    for ci, cp in enumerate(checkpoints):
        result.append({
            "checkpoint_code": cp["code"],
            "checkpoint_label": cp["label"],
            "is_required": cp.get("required", True),
            "is_sample_level": cp.get("is_sample_level", False),
            "checkpoint_group": cp.get("checkpoint_group", ""),
            "sort_order": ci + 1,
        })
    return result


def _build_prechecks(code: str) -> list[dict]:
    """构建预检查项: 通用母版过程确认 + 各实验专属补充"""
    kind = EXPERIMENT_META[code]["kind"]
    names_seen: set[str] = set()
    result: list[dict] = []

    for pf in COMMON_PROCESS_OBSERVATIONS:
        if pf["key"] not in names_seen:
            result.append({
                "precheck_code": pf["key"],
                "precheck_label": pf["label"],
                "is_required": True,
                "sort_order": len(result) + 1,
            })
            names_seen.add(pf["key"])

    supplemental = SUPPLEMENTAL_PROCESS_FIELDS.get(kind, [])
    for sf in supplemental:
        if sf["key"] not in names_seen:
            result.append({
                "precheck_code": sf["key"],
                "precheck_label": sf["label"],
                "is_required": True,
                "sort_order": len(result) + 1,
            })
            names_seen.add(sf["key"])

    return result


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def _asyncpg_url() -> str:
    """将 SQLAlchemy URL 转成 asyncpg 可用的 postgresql:// 格式"""
    raw = settings.DATABASE_URL
    # 去掉 +asyncpg / +psycopg2 等方言前缀
    for dialect in ("+asyncpg", "+psycopg2", "+aiopg", "+pg8000"):
        raw = raw.replace(dialect, "")
    return raw


async def seed():
    conn = await asyncpg.connect(_asyncpg_url())
    try:
        for code in sorted(EXPERIMENT_META.keys()):
            meta = EXPERIMENT_META[code]
            name = meta["name"]
            kind = meta["kind"]

            print(f"--- {code} {name} ---")

            # 1. 标记旧版本为历史
            old = await conn.fetchval(
                "SELECT id FROM experiment_config_versions "
                "WHERE experiment_code=$1 AND status='现行'",
                code,
            )
            if old:
                await conn.execute(
                    "UPDATE experiment_config_versions SET status='历史' WHERE id=$1", old
                )
                print(f"  [OK] Old version id={old} -> history")

            # 2. 确认 experiment_methods 有记录
            method_exists = await conn.fetchval(
                "SELECT 1 FROM experiment_methods WHERE experiment_code=$1", code
            )
            if not method_exists:
                await conn.execute(
                    """INSERT INTO experiment_methods
                       (experiment_code, experiment_name, kind, method_code, standard, category,
                        enabled, created_at)
                       VALUES ($1,$2,$3,$4,$5,$6,TRUE,localtimestamp)
                       ON CONFLICT (experiment_code) DO NOTHING""",
                    code, name, kind, meta["method"], meta["standard"], meta["category"],
                )
                print(f"  [+] Added experiment_methods record")

            # 3. 插入新版本 (upsert)
            config_id = await conn.fetchval(
                """INSERT INTO experiment_config_versions
                   (experiment_code, version, experiment_name, method_code, standard,
                    category, kind, default_location, status, effective_date, note, created_by)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'现行',$9,$10,'seed_configs.py')
                   ON CONFLICT (experiment_code, version) DO UPDATE
                   SET experiment_name=EXCLUDED.experiment_name,
                       method_code=EXCLUDED.method_code,
                       standard=EXCLUDED.standard,
                       category=EXCLUDED.category,
                       kind=EXCLUDED.kind,
                       default_location=EXCLUDED.default_location,
                       status='现行',
                       effective_date=EXCLUDED.effective_date,
                       note=EXCLUDED.note
                   RETURNING id""",
                code, SEED_VERSION, name, meta["method"], meta["standard"],
                meta["category"], kind, meta["location"], date.today(), SEED_NOTE,
            )
            print(f"  [OK] 配置版本 id={config_id} ({SEED_VERSION})")

            # 4. 清空旧子记录
            for tbl in ["experiment_config_fields", "experiment_config_columns",
                         "experiment_config_photo_checkpoints", "experiment_config_prechecks",
                         "experiment_config_equipment"]:
                await conn.execute(f"DELETE FROM {tbl} WHERE config_id=$1", config_id)

            # 5. 插入字段
            fields = _build_fields(code)
            for f in fields:
                await conn.execute(
                    """INSERT INTO experiment_config_fields
                       (config_id, section_title, section_order, field_key, field_label,
                        field_type, field_default, field_options,
                        is_required, is_readonly, is_actual, sort_order)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
                    config_id,
                    f["section_title"], f["section_order"], f["field_key"], f["field_label"],
                    f["field_type"], f["field_default"], f["field_options"],
                    f["is_required"], f["is_readonly"], f["is_actual"], f["sort_order"],
                )
            print(f"  [OK] 字段: {len(fields)}")

            # 6. 插入测量列
            columns = _build_columns(code)
            for c in columns:
                await conn.execute(
                    """INSERT INTO experiment_config_columns
                       (config_id, column_key, column_label, column_type, is_required,
                        column_default, calc_expression, calc_precision, sort_order)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
                    config_id,
                    c["column_key"], c["column_label"], c["column_type"],
                    c.get("is_required", True),
                    c.get("column_default", ""),
                    c.get("calc_expression", ""),
                    c.get("calc_precision", 3),
                    c["sort_order"],
                )
            print(f"  [OK] 测量列: {len(columns)}")

            # 7. 插入拍照节点
            photos = _build_photos(code)
            for p in photos:
                await conn.execute(
                    """INSERT INTO experiment_config_photo_checkpoints
                       (config_id, checkpoint_code, checkpoint_label, is_required,
                        is_sample_level, checkpoint_group, sort_order)
                       VALUES ($1,$2,$3,$4,$5,$6,$7)""",
                    config_id,
                    p["checkpoint_code"], p["checkpoint_label"], p["is_required"],
                    p["is_sample_level"], p["checkpoint_group"], p["sort_order"],
                )
            print(f"  [OK] 拍照节点: {len(photos)}")

            # 8. 插入预检查项
            prechecks = _build_prechecks(code)
            for pk in prechecks:
                await conn.execute(
                    """INSERT INTO experiment_config_prechecks
                       (config_id, precheck_code, precheck_label, is_required, sort_order)
                       VALUES ($1,$2,$3,$4,$5)""",
                    config_id,
                    pk["precheck_code"], pk["precheck_label"], pk["is_required"], pk["sort_order"],
                )
            print(f"  [OK] 预检查项: {len(prechecks)}")

            # 9. 从 experiment_equipment_bindings 复制设备绑定
            eq_rows = await conn.fetch(
                """SELECT eeb.*, er.equipment_name, er.model
                   FROM experiment_equipment_bindings eeb
                   LEFT JOIN equipment_registry er ON eeb.management_no = er.management_no
                   WHERE eeb.experiment = $1
                   ORDER BY eeb.sort_order""",
                name,
            )
            for ei, eq in enumerate(eq_rows):
                await conn.execute(
                    """INSERT INTO experiment_config_equipment
                       (config_id, management_no, binding_role, required, sort_order, note)
                       VALUES ($1,$2,$3,$4,$5,$6)""",
                    config_id,
                    eq["management_no"],
                    eq.get("usage_role", eq.get("binding_role", "主要设备")),
                    True if eq.get("required", False) else False,
                    ei + 1,
                    eq.get("note", ""),
                )
            print(f"  [OK] 设备绑定: {len(eq_rows)}")

        print(f"\n{'='*60}")
        print(f"[OK] 全部完成! {len(EXPERIMENT_META)} 个实验配置已更新到 {SEED_VERSION}")
        print(f"{'='*60}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
