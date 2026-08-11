"""
Auto-seed 模块 —— 首次启动时自动填充基础数据

在 app/main.py 的 lifespan 中调用 auto_seed()。
如果 experiment_methods 表为空，则自动填充：
  1. 14 项实验方法
  2. 12 项实验配置版本 (I001-I012, V2.0)
  3. 设备数据 (从 CSV 读取，若可用)
  4. 设备绑定关系 (从 CSV 读取，若可用)

数据来源：
  - 实验方法: 硬编码 (与 seed_v10.py 一致)
  - 实验配置: app.core.experiment_schemas (与 seed_configs.py 一致)
  - 设备/绑定: CSV 文件 (可选，路径见 EQUIPMENT_CSV / BINDING_CSV)
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import date
from pathlib import Path
from typing import Sequence

from sqlalchemy import text
from app.database import async_session

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 14 项实验方法 (与 seed_v10.py 一致)
# ═══════════════════════════════════════════════════════════════
EXPERIMENT_METHODS: list[tuple[str, str, str, str, str]] = [
    ("I001", "表面粗糙度试验",        "YY/T 1702",   "YY/T 1702-2020",               "rough"),
    ("I002", "金属-陶瓷结合裂纹萌生试验", "YY 0621.1",  "YY 0621.1-2016 / ISO 9693-1",  "crack"),
    ("I003", "金属内部质量X射线灰度分析",  "GB 17168",    "GB 17168-2013",                 "xray"),
    ("I004", "翘曲变形试验",           "YY/T 1702",   "YY/T 1702-2020",               "warpage"),
    ("I005", "热膨胀系数试验",          "YY 0621.1",   "YY 0621.1-2016",               "cte"),
    ("I006", "陶瓷牙耐急冷急热试验",      "YY 0300",     "YY 0300-2009",                "thermal_shock"),
    ("I007", "弯曲性能试验",           "YY/T 1702",   "YY/T 1702-2020",               "bending"),
    ("I008", "维氏硬度试验",           "GB/T 4340.1", "GB/T 4340.1-2024",             "vickers"),
    ("I009", "增材制造金属试样厚度测量",    "YY/T 1702",   "YY/T 1702-2020",               "thickness"),
    ("I010", "牙科材料色稳定性试验",      "YY 0710",     "YY 0710-2009",                "color_stability"),
    ("I011", "定制式固定义齿检验",       "GB 17168",    "GB 17168-2013",                "fixed_denture"),
    ("I012", "定制式活动义齿检验",       "GB 17168",    "GB 17168-2013",                "removable_denture"),
    ("I013", "激光选区熔化金属材料密度试验",  "YY/T 1702",   "YY/T 1702-2020",               "density"),
    ("I014", "金属材料抗晦暗性能试验",     "YY 0710",     "YY 0710-2009",                "tarnish"),
]

# ═══════════════════════════════════════════════════════════════
# CSV 路径（可选，不存在则跳过设备导入）
# ═══════════════════════════════════════════════════════════════
_ROOT = Path(__file__).parent.parent.parent.parent  # backend/../ → 项目根目录
_EQUIPMENT_CSV = _ROOT / "资料" / "bplab_v10_update" / "bplab_v10_template_update" / "equipment_master.csv"
_BINDING_CSV   = _ROOT / "资料" / "bplab_v10_update" / "bplab_v10_template_update" / "equipment_binding_matrix.csv"

# 也可通过环境变量覆盖 CSV 路径
EQUIPMENT_CSV = Path(os.getenv("SEED_EQUIPMENT_CSV", str(_EQUIPMENT_CSV)))
BINDING_CSV   = Path(os.getenv("SEED_BINDING_CSV",   str(_BINDING_CSV)))


# ═══════════════════════════════════════════════════════════════
# 实验配置元数据 (与 seed_configs.py 一致)
# ═══════════════════════════════════════════════════════════════
_EXPERIMENT_META: dict[str, dict] = {
    "I001": {"name": "表面粗糙度试验",           "kind": "rough",    "method": "YY/T 1702",
             "standard": "YY/T 1702-2020；GB/T 10610-2009", "category": "增材制造检测",  "location": "显微检测室"},
    "I002": {"name": "金属-陶瓷结合裂纹萌生试验",   "kind": "mc_crack", "method": "YY 0621.1",
             "standard": "YY 0621.1-2016 / ISO 9693-1",    "category": "力学性能检测",  "location": "性能检测室"},
    "I003": {"name": "金属内部质量X射线灰度分析",    "kind": "xray",     "method": "GB 17168",
             "standard": "GB 17168及实验室受控SOP",           "category": "内部质量检测",  "location": "无损检测室"},
    "I004": {"name": "翘曲变形试验",             "kind": "warp",     "method": "YY/T 1702",
             "standard": "YY/T 1702-2020 第7.3.2条",         "category": "增材制造检测",  "location": "显微检测室"},
    "I005": {"name": "热膨胀系数试验",            "kind": "cte",      "method": "YY 0621.1",
             "standard": "YY 0621.1及实验室受控SOP",           "category": "物理性能检测",  "location": "性能检测室"},
    "I006": {"name": "陶瓷牙耐急冷急热试验",        "kind": "shock",    "method": "YY 0300",
             "standard": "YY 0300-2009 第7.10条",           "category": "陶瓷材料检测",  "location": "性能检测室"},
    "I007": {"name": "弯曲性能试验",             "kind": "bend",     "method": "YY/T 1702",
             "standard": "YY/T 1702-2020",                 "category": "力学性能检测",  "location": "性能检测室"},
    "I008": {"name": "维氏硬度试验",             "kind": "hv",       "method": "GB/T 4340.1",
             "standard": "GB/T 4340.1-2024",               "category": "力学性能检测",  "location": "显微检测室"},
    "I009": {"name": "增材制造金属试样厚度测量",      "kind": "thickness","method": "YY/T 1702",
             "standard": "YY/T 1702-2020",                 "category": "增材制造检测",  "location": "显微检测室"},
    "I010": {"name": "牙科材料色稳定性试验",        "kind": "color",    "method": "YY 0710",
             "standard": "YY 0710及产品技术要求",             "category": "物理性能检测",  "location": "外观检测室"},
    "I011": {"name": "定制式固定义齿综合检验",      "kind": "fixed_denture", "method": "YY/T 1936",
             "standard": "YY/T 1936及产品技术要求",          "category": "定制式义齿",   "location": "外观检测室"},
    "I012": {"name": "定制式活动义齿综合检验",      "kind": "removable_denture", "method": "YY 0270.1",
             "standard": "YY 0270.1及产品技术要求",          "category": "定制式义齿",   "location": "外观检测室"},
}

SEED_VERSION = "V2.0"
SEED_NOTE = f"auto-seed 首次启动自动创建 ({date.today().isoformat()})"


# ═══════════════════════════════════════════════════════════════
# 拍照节点 (与 seed_configs.py 一致)
# ═══════════════════════════════════════════════════════════════
_COMMON_PHOTO_CHECKPOINTS = [
    {"code": "ENV",          "label": "实验开始温湿度表",               "required": False, "sample_level": False, "group": "环境与设备"},
    {"code": "SAMPLE_BEFORE","label": "实验前样品及标签",               "required": False, "sample_level": False, "group": "样品状态"},
    {"code": "DEVICE",       "label": "设备编号/铭牌",                  "required": False, "sample_level": False, "group": "环境与设备"},
    {"code": "PARAMETERS",   "label": "设备参数或软件数据界面",           "required": False, "sample_level": False, "group": "环境与设备"},
    {"code": "SETUP",        "label": "样品安装、装夹或放置状态",         "required": False, "sample_level": False, "group": "样品状态"},
    {"code": "RESULT",       "label": "最终读数、曲线或结果界面",         "required": False, "sample_level": False, "group": "结果界面"},
    {"code": "SAMPLE_AFTER", "label": "实验结束后样品状态",              "required": False, "sample_level": False, "group": "样品状态"},
    {"code": "REPORT_PHOTO", "label": "检验报告照片区域用代表性照片",     "required": False, "sample_level": False, "group": "报告归档"},
]

_EXPERIMENT_PHOTO_CHECKPOINTS: dict[str, list[dict]] = {
    "表面粗糙度试验": [
        {"code": "ROUGH_POINT_1","label": "测量点①拍照","required": True,"sample_level": True,"group": "测量点"},
        {"code": "ROUGH_POINT_2","label": "测量点②拍照","required": True,"sample_level": True,"group": "测量点"},
        {"code": "ROUGH_POINT_3","label": "测量点③拍照","required": True,"sample_level": True,"group": "测量点"},
        {"code": "ROUGH_CURVE_RESULT","label": "测量曲线、计算设置与结果界面","required": True,"sample_level": False,"group": "结果界面"},
    ],
    "金属-陶瓷结合裂纹萌生试验": [
        {"code": "MC_K_VALUE","label": "试样K值拍照","required": True,"sample_level": True,"group": "结果界面"},
        {"code": "MC_REPORT","label": "报告拍照","required": True,"sample_level": True,"group": "结果界面"},
    ],
    "金属内部质量X射线灰度分析": [
        {"code": "IQI_POSITION","label": "样品与孔形像质计摆放","required": False,"sample_level": False,"group": "装夹与核查"},
        {"code": "EXPOSURE","label": "曝光参数界面","required": False,"sample_level": False,"group": "环境与设备"},
        {"code": "RADIOGRAPH","label": "原始X射线成像画面","required": True,"sample_level": True,"group": "结果界面"},
        {"code": "ROI","label": "ROI位置及灰度值","required": True,"sample_level": True,"group": "结果界面"},
    ],
    "翘曲变形试验": [
        {"code": "H1_BASELINE","label": "切割前基准线到自由端中点距离","required": True,"sample_level": True,"group": "结果界面"},
        {"code": "H2_BASELINE","label": "切割后基准线到自由端中点距离","required": True,"sample_level": True,"group": "结果界面"},
        {"code": "WARP_REPORT_1","label": "试验报告拍照①","required": True,"sample_level": False,"group": "结果界面"},
        {"code": "WARP_REPORT_2","label": "试验报告拍照②","required": True,"sample_level": False,"group": "结果界面"},
        {"code": "WARP_REPORT_3","label": "试验报告拍照③","required": True,"sample_level": False,"group": "结果界面"},
    ],
    "热膨胀系数试验": [
        {"code": "CTE_PARAM_SET","label": "试验参数设定拍照","required": True,"sample_level": False,"group": "环境与设备"},
        {"code": "CTE_REPORT","label": "样品试验报告拍照","required": True,"sample_level": False,"group": "结果界面"},
    ],
    "陶瓷牙耐急冷急热试验": [
        {"code": "SHOCK_BEFORE","label": "试验前试样拍照","required": True,"sample_level": True,"group": "样品状态"},
        {"code": "SHOCK_AFTER","label": "试验后试样拍照","required": True,"sample_level": True,"group": "样品状态"},
        {"code": "OVEN_TEMP","label": "烘箱100±2℃实测温度","required": False,"sample_level": False,"group": "环境与设备"},
        {"code": "ICE_TEMP_START","label": "试验前冰水1±1℃温度","required": False,"sample_level": False,"group": "环境与设备"},
        {"code": "ICE_TEMP_PROCESS","label": "试验中每15分钟冰水复测读数","required": False,"sample_level": False,"group": "环境与设备"},
        {"code": "FIRST_HEAT","label": "第一次加热开始/结束时间与温度","required": False,"sample_level": False,"group": "过程记录"},
        {"code": "TRANSFER_COLD","label": "急冷转移、浸没状态与时间","required": False,"sample_level": False,"group": "过程记录"},
        {"code": "SECOND_HEAT","label": "第二次加热时间与温度","required": False,"sample_level": False,"group": "过程记录"},
        {"code": "COOL_TEMP","label": "自然冷却后样品表面23±2℃","required": False,"sample_level": False,"group": "过程记录"},
        {"code": "INSPECTION_LIGHT","label": "外观检查光照度≥1000 lx","required": False,"sample_level": False,"group": "核查与设备"},
        {"code": "DAMAGE","label": "逐颗裂纹、崩瓷或破损检查结果","required": False,"sample_level": True,"group": "结果界面"},
    ],
    "弯曲性能试验": [
        {"code": "BEND_REPORT","label": "报告拍照","required": True,"sample_level": True,"group": "结果界面"},
    ],
    "维氏硬度试验": [
        {"code": "HV_LOAD_TIME","label": "载荷和保荷时间","required": True,"sample_level": False,"group": "环境与设备"},
        {"code": "HV_REPORT_1","label": "报告拍照①","required": True,"sample_level": True,"group": "结果界面"},
        {"code": "HV_REPORT_2","label": "报告拍照②","required": True,"sample_level": True,"group": "结果界面"},
    ],
    "增材制造金属试样厚度测量": [
        {"code": "FIXED_DIST_1","label": "固定端距离拍照①","required": True,"sample_level": True,"group": "测量点"},
        {"code": "FIXED_DIST_2","label": "固定端距离拍照②","required": True,"sample_level": True,"group": "测量点"},
        {"code": "FIXED_DIST_3","label": "固定端距离拍照③","required": True,"sample_level": True,"group": "测量点"},
        {"code": "MID_DIST_1","label": "中间距离拍照①","required": True,"sample_level": True,"group": "测量点"},
        {"code": "MID_DIST_2","label": "中间距离拍照②","required": True,"sample_level": True,"group": "测量点"},
        {"code": "MID_DIST_3","label": "中间距离拍照③","required": True,"sample_level": True,"group": "测量点"},
        {"code": "FREE_END_1","label": "自由端拍照①","required": True,"sample_level": True,"group": "测量点"},
        {"code": "FREE_END_2","label": "自由端拍照②","required": True,"sample_level": True,"group": "测量点"},
        {"code": "FREE_END_3","label": "自由端拍照③","required": True,"sample_level": True,"group": "测量点"},
        {"code": "THICK_REPORT","label": "报告拍照","required": True,"sample_level": True,"group": "结果界面"},
    ],
    "牙科材料色稳定性试验": [
        {"code": "COLOR_BEFORE","label": "试验前试样拍照","required": True,"sample_level": True,"group": "样品状态"},
        {"code": "COLOR_AFTER","label": "试验后试样拍照","required": True,"sample_level": True,"group": "样品状态"},
    ],
    "定制式固定义齿综合检验": [
        {"code": "DESIGN_TRACE","label": "设计单、模型及原材料追溯核查","required": True,"sample_level": False,"group": "装夹与核查"},
        {"code": "FIXED_DENTURE_RESULT","label": "表面、适合性、咬合及尺寸综合检验结果","required": True,"sample_level": True,"group": "结果界面"},
        {"code": "MICRO_RESULT","label": "粗糙度或孔隙度显微检查结果","required": False,"sample_level": False,"group": "结果界面"},
    ],
    "定制式活动义齿综合检验": [
        {"code": "DESIGN_TRACE","label": "设计单、模型及原材料追溯核查","required": True,"sample_level": False,"group": "装夹与核查"},
        {"code": "REMOVABLE_DENTURE_RESULT","label": "外形、适合性、厚度及咬合综合检验结果","required": True,"sample_level": True,"group": "结果界面"},
        {"code": "XRAY_RESULT","label": "金属内部质量X射线结果","required": False,"sample_level": True,"group": "结果界面"},
        {"code": "COLOR_RESULT","label": "色泽检查结果","required": False,"sample_level": True,"group": "结果界面"},
    ],
}

_KINDS_ONLY_SPECIFIC = {"rough", "mc_crack", "cte", "hv", "thickness", "bend"}


# ═══════════════════════════════════════════════════════════════
# 测量列默认值 (与 seed_configs.py 一致)
# ═══════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

async def auto_seed() -> dict:
    """首次启动时自动填充基础数据。幂等操作——已存在的数据不会重复插入。

    返回:
        dict: {"methods": int, "configs": int, "equipment": int, "bindings": int}
    """
    result = {"methods": 0, "configs": 0, "equipment": 0, "bindings": 0}

    async with async_session() as db:
        try:
            # 1. 实验方法
            count = await db.execute(text("SELECT COUNT(*) FROM experiment_methods"))
            if count.fetchone()[0] == 0:
                logger.info("实验方法表为空，开始自动填充…")
                result["methods"] = await _seed_methods(db)
                await db.commit()
                logger.info(f"实验方法填充完成: {result['methods']} 条")
            else:
                logger.info("实验方法表已有数据，跳过。")

            # 2. 设备（CSV 可选）
            if EQUIPMENT_CSV.exists():
                equip_count = await db.execute(text("SELECT COUNT(*) FROM equipment_registry"))
                if equip_count.fetchone()[0] == 0:
                    logger.info(f"设备表为空，从 CSV 导入: {EQUIPMENT_CSV}")
                    result["equipment"] = await _seed_equipment(db)
                    await db.commit()
                    logger.info(f"设备导入完成: {result['equipment']} 条")
                else:
                    logger.info("设备表已有数据，跳过。")
            else:
                logger.warning(f"设备 CSV 未找到 ({EQUIPMENT_CSV})，跳过设备导入。")

            # 3. 设备绑定（CSV 可选）
            if BINDING_CSV.exists():
                binding_count = await db.execute(text("SELECT COUNT(*) FROM experiment_equipment_bindings"))
                if binding_count.fetchone()[0] == 0:
                    logger.info(f"设备绑定表为空，从 CSV 导入: {BINDING_CSV}")
                    result["bindings"] = await _seed_bindings(db)
                    await db.commit()
                    logger.info(f"设备绑定导入完成: {result['bindings']} 条")
                else:
                    logger.info("设备绑定表已有数据，跳过。")
            else:
                logger.warning(f"绑定 CSV 未找到 ({BINDING_CSV})，跳过绑定导入。")

            # 4. 实验配置版本
            config_count = await db.execute(text("SELECT COUNT(*) FROM experiment_config_versions"))
            if config_count.fetchone()[0] == 0:
                logger.info("实验配置表为空，开始自动填充…")
                result["configs"] = await _seed_configs(db)
                await db.commit()
                logger.info(f"实验配置填充完成: {result['configs']} 个")
            else:
                logger.info("实验配置表已有数据，跳过。")

        except Exception:
            await db.rollback()
            logger.exception("自动种子数据失败！")
            raise

    return result


# ═══════════════════════════════════════════════════════════════
# 子任务
# ═══════════════════════════════════════════════════════════════

async def _seed_methods(db) -> int:
    """插入 14 项实验方法 (幂等)"""
    count = 0
    for code, name, method, standard, kind in EXPERIMENT_METHODS:
        existing = await db.execute(
            text("SELECT 1 FROM experiment_methods WHERE experiment_code=:c"), {"c": code}
        )
        if existing.fetchone():
            await db.execute(
                text("""UPDATE experiment_methods SET experiment_name=:n, method_code=:m,
                        standard=:s, kind=:k, updated_at=localtimestamp
                        WHERE experiment_code=:c"""),
                {"n": name, "m": method, "s": standard, "k": kind, "c": code},
            )
        else:
            await db.execute(
                text("""INSERT INTO experiment_methods (experiment_code, experiment_name,
                        method_code, standard, kind, enabled, created_at, updated_at)
                        VALUES (:c,:n,:m,:s,:k,TRUE,localtimestamp,localtimestamp)"""),
                {"c": code, "n": name, "m": method, "s": standard, "k": kind},
            )
            count += 1
    return count


async def _seed_equipment(db) -> int:
    """从 CSV 导入设备 (幂等: management_no 去重)"""
    inserted, updated = 0, 0
    with open(EQUIPMENT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        mgmt_no = (row.get("管理编号") or "").strip()
        if not mgmt_no:
            continue

        name = (row.get("名称") or "").strip()
        model = (row.get("规格型号") or "").strip()
        measuring_range = (row.get("测量范围") or "").strip()
        manufacturer = (row.get("生产厂家") or "").strip()
        serial_no = (row.get("出厂编号") or "").strip()
        purchase_time = (row.get("购置时间") or "").strip()
        calibration_time = (row.get("校准时间") or "").strip()
        responsible = (row.get("责任人") or "").strip()
        equip_class = (row.get("分类") or "").strip()

        existing = await db.execute(
            text("SELECT 1 FROM equipment_registry WHERE management_no=:m"), {"m": mgmt_no}
        )
        if existing.fetchone():
            await db.execute(
                text("""UPDATE equipment_registry SET equipment_name=:en, model=:md,
                        measuring_range=:mr, manufacturer=:mf, serial_no=:sn,
                        purchase_time=:pd, calibration_time=:ct, responsible=:rp,
                        equipment_class=:ec, lifecycle_status='启用', updated_at=localtimestamp
                        WHERE management_no=:mn"""),
                {"en": name, "md": model, "mr": measuring_range, "mf": manufacturer,
                 "sn": serial_no, "pd": purchase_time if purchase_time else None,
                 "ct": calibration_time if calibration_time else None, "rp": responsible,
                 "ec": equip_class, "mn": mgmt_no},
            )
            updated += 1
        else:
            await db.execute(
                text("""INSERT INTO equipment_registry (management_no, equipment_name, model,
                        measuring_range, manufacturer, serial_no, purchase_time,
                        calibration_time, responsible, equipment_class,
                        lifecycle_status, enabled, created_at, updated_at)
                        VALUES (:mn,:en,:md,:mr,:mf,:sn,:pd,:ct,:rp,:ec,
                        '启用',TRUE,localtimestamp,localtimestamp)"""),
                {"mn": mgmt_no, "en": name, "md": model, "mr": measuring_range,
                 "mf": manufacturer, "sn": serial_no,
                 "pd": purchase_time if purchase_time else None,
                 "ct": calibration_time if calibration_time else None,
                 "rp": responsible, "ec": equip_class},
            )
            inserted += 1

    logger.info(f"  设备: 新增 {inserted}, 更新 {updated}")
    return inserted + updated


async def _seed_bindings(db) -> int:
    """从 CSV 导入设备-实验绑定"""
    await db.execute(text("DELETE FROM experiment_equipment_bindings"))
    count = 0
    with open(BINDING_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            experiment = (row.get("实验名称") or "").strip()
            mgmt_no = (row.get("管理编号") or "").strip()
            if not experiment or not mgmt_no:
                continue
            await db.execute(
                text("""INSERT INTO experiment_equipment_bindings
                        (experiment, management_no, binding_role, required, note, created_at, updated_at)
                        VALUES (:ex,:mn,:br,:rq,:nt,localtimestamp,localtimestamp)"""),
                {"ex": experiment, "mn": mgmt_no,
                 "br": (row.get("设备角色") or "").strip(),
                 "rq": (row.get("是否必需") or "是").strip() == "是",
                 "nt": (row.get("用途/绑定说明") or "").strip()},
            )
            count += 1
    logger.info(f"  设备绑定: {count} 条")
    return count


# ═══════════════════════════════════════════════════════════════
# 实验配置 (I001-I012, V2.0)
# ═══════════════════════════════════════════════════════════════

async def _seed_configs(db) -> int:
    """为 I001-I012 创建 V2.0 配置版本 + 字段 + 列 + 拍照 + 预检 + 设备绑定"""
    from .experiment_schemas import SCHEMAS, COMMON_PROCESS_OBSERVATIONS, SUPPLEMENTAL_PROCESS_FIELDS

    count = 0
    for code in sorted(_EXPERIMENT_META.keys()):
        meta = _EXPERIMENT_META[code]
        name = meta["name"]
        kind = meta["kind"]

        logger.info(f"  {code} {name} …")

        # 标记旧版本为历史
        old = await db.execute(
            text("SELECT id FROM experiment_config_versions WHERE experiment_code=:c AND status='现行'"),
            {"c": code},
        )
        old_id = old.fetchone()
        if old_id:
            await db.execute(
                text("UPDATE experiment_config_versions SET status='历史' WHERE id=:i"),
                {"i": old_id[0]},
            )

        # 补充 experiment_methods 记录（seed_configs 不依赖 seed_v10）
        method_exists = await db.execute(
            text("SELECT 1 FROM experiment_methods WHERE experiment_code=:c"), {"c": code}
        )
        if not method_exists.fetchone():
            await db.execute(
                text("""INSERT INTO experiment_methods (experiment_code, experiment_name, kind,
                        method_code, standard, category, enabled, created_at)
                        VALUES (:c,:n,:k,:m,:s,:cat,TRUE,localtimestamp)
                        ON CONFLICT (experiment_code) DO NOTHING"""),
                {"c": code, "n": name, "k": kind, "m": meta["method"],
                 "s": meta["standard"], "cat": meta["category"]},
            )

        # 插入配置版本 (upsert)
        result = await db.execute(
            text("""INSERT INTO experiment_config_versions
                    (experiment_code, version, experiment_name, method_code, standard,
                     category, kind, default_location, status, effective_date, note, created_by)
                    VALUES (:c,:v,:n,:m,:s,:cat,:k,:loc,'现行',:ed,:note,'auto_seed')
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
                    RETURNING id"""),
            {"c": code, "v": SEED_VERSION, "n": name, "m": meta["method"],
             "s": meta["standard"], "cat": meta["category"], "k": kind,
             "loc": meta["location"], "ed": date.today(), "note": SEED_NOTE},
        )
        config_id = result.fetchone()[0]

        # 清空旧子记录
        for tbl in ["experiment_config_fields", "experiment_config_columns",
                     "experiment_config_photo_checkpoints", "experiment_config_prechecks",
                     "experiment_config_equipment"]:
            await db.execute(text(f"DELETE FROM {tbl} WHERE config_id=:cid"), {"cid": config_id})

        # 字段
        fields = _build_fields(code, kind, SCHEMAS)
        for f in fields:
            await db.execute(
                text("""INSERT INTO experiment_config_fields
                        (config_id, section_title, section_order, field_key, field_label,
                         field_type, field_default, field_options, is_required, is_readonly,
                         is_actual, sort_order)
                        VALUES (:cid,:st,:so,:fk,:fl,:ft,:fd,:fo,:ir,:iro,:ia,:srt)"""),
                {"cid": config_id, "st": f["section_title"], "so": f["section_order"],
                 "fk": f["field_key"], "fl": f["field_label"], "ft": f["field_type"],
                 "fd": f["field_default"], "fo": f["field_options"],
                 "ir": f["is_required"], "iro": f["is_readonly"], "ia": f["is_actual"],
                 "srt": f["sort_order"]},
            )
        logger.info(f"    字段: {len(fields)}")

        # 测量列
        columns = _build_columns(code, kind, SCHEMAS)
        for c in columns:
            await db.execute(
                text("""INSERT INTO experiment_config_columns
                        (config_id, column_key, column_label, column_type, is_required,
                         column_default, calc_expression, calc_precision, sort_order)
                        VALUES (:cid,:ck,:cl,:ct,:ir,:cd,:ce,:cp,:so)"""),
                {"cid": config_id, "ck": c["column_key"], "cl": c["column_label"],
                 "ct": c["column_type"], "ir": c.get("is_required", True),
                 "cd": c.get("column_default", ""), "ce": c.get("calc_expression", ""),
                 "cp": c.get("calc_precision", 3), "so": c["sort_order"]},
            )
        logger.info(f"    测量列: {len(columns)}")

        # 拍照节点
        photos = _build_photos(code, kind, name)
        for p in photos:
            await db.execute(
                text("""INSERT INTO experiment_config_photo_checkpoints
                        (config_id, checkpoint_code, checkpoint_label, is_required,
                         is_sample_level, checkpoint_group, sort_order)
                        VALUES (:cid,:cc,:cl,:ir,:isl,:cg,:so)"""),
                {"cid": config_id, "cc": p["checkpoint_code"], "cl": p["checkpoint_label"],
                 "ir": p["is_required"], "isl": p["is_sample_level"],
                 "cg": p["checkpoint_group"], "so": p["sort_order"]},
            )
        logger.info(f"    拍照节点: {len(photos)}")

        # 预检查项
        prechecks = _build_prechecks(code, kind, COMMON_PROCESS_OBSERVATIONS, SUPPLEMENTAL_PROCESS_FIELDS)
        for pk in prechecks:
            await db.execute(
                text("""INSERT INTO experiment_config_prechecks
                        (config_id, precheck_code, precheck_label, is_required, sort_order)
                        VALUES (:cid,:pc,:pl,:ir,:so)"""),
                {"cid": config_id, "pc": pk["precheck_code"], "pl": pk["precheck_label"],
                 "ir": pk["is_required"], "so": pk["sort_order"]},
            )
        logger.info(f"    预检查项: {len(prechecks)}")

        # 设备绑定 (从 experiment_equipment_bindings 表复制)
        eq_rows = await db.execute(
            text("""SELECT eeb.*, er.equipment_name, er.model
                    FROM experiment_equipment_bindings eeb
                    LEFT JOIN equipment_registry er ON eeb.management_no = er.management_no
                    WHERE eeb.experiment = :n
                    ORDER BY eeb.sort_order"""),
            {"n": name},
        )
        eq_list = eq_rows.fetchall()
        for ei, eq in enumerate(eq_list):
            await db.execute(
                text("""INSERT INTO experiment_config_equipment
                        (config_id, management_no, binding_role, required, sort_order, note)
                        VALUES (:cid,:mn,:br,:rq,:so,:nt)"""),
                {"cid": config_id, "mn": eq.management_no,
                 "br": getattr(eq, "binding_role", "主要设备"),
                 "rq": bool(getattr(eq, "required", False)),
                 "so": ei + 1,
                 "nt": getattr(eq, "note", "") or ""},
            )
        logger.info(f"    设备绑定: {len(eq_list)}")

        count += 1

    return count


# ═══════════════════════════════════════════════════════════════
# 子构建函数
# ═══════════════════════════════════════════════════════════════

def _build_fields(code: str, kind: str, schemas: dict) -> list[dict]:
    schema = schemas.get(kind)
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
                "section_title": title, "section_order": si + 1,
                "field_key": f.get("key", ""), "field_label": f.get("label", ""),
                "field_type": f.get("type", "text"), "field_default": default_str,
                "field_options": ",".join(f.get("options", [])) if f.get("options") else "",
                "is_required": f.get("required", False), "is_readonly": f.get("readonly", False),
                "is_actual": f.get("actual", False), "sort_order": fi + 1,
            })
    return result


def _build_columns(code: str, kind: str, schemas: dict) -> list[dict]:
    schema = schemas.get(kind)
    if not schema:
        return []
    result = []
    for ci, col in enumerate(schema.get("columns", [])):
        if isinstance(col, (list, tuple)) and len(col) >= 2:
            col_type = col[2] if len(col) >= 3 else "text"
            if col_type.startswith("select:"):
                opts = col_type.split(":", 1)[1]
                col_type = "select"
            else:
                opts = ""
            num_default = _COLUMN_DEFAULTS.get((kind, col[0]))
            if num_default is not None:
                default_val = str(num_default)
            elif opts:
                default_val = opts
            else:
                default_val = ""
            entry = {
                "column_key": col[0], "column_label": col[1],
                "column_type": col_type, "is_required": True,
                "column_default": default_val, "calc_expression": "",
                "calc_precision": 3, "sort_order": ci + 1,
            }
            if col_type == "calc":
                entry["calc_expression"] = col[1]
                entry["calc_precision"] = 3
            result.append(entry)
    return result


def _build_photos(code: str, kind: str, name: str) -> list[dict]:
    specific = _EXPERIMENT_PHOTO_CHECKPOINTS.get(name, [])
    if kind in _KINDS_ONLY_SPECIFIC and specific:
        checkpoints: Sequence[dict] = list(specific)
    elif specific:
        checkpoints = list(_COMMON_PHOTO_CHECKPOINTS) + list(specific)
    else:
        checkpoints = list(_COMMON_PHOTO_CHECKPOINTS)

    result = []
    for ci, cp in enumerate(checkpoints):
        result.append({
            "checkpoint_code": cp["code"], "checkpoint_label": cp["label"],
            "is_required": cp.get("required", True),
            "is_sample_level": cp.get("sample_level", False),
            "checkpoint_group": cp.get("group", ""), "sort_order": ci + 1,
        })
    return result


def _build_prechecks(code: str, kind: str,
                     common: list[dict], supplemental: dict) -> list[dict]:
    names_seen: set[str] = set()
    result: list[dict] = []

    for pf in common:
        if pf["key"] not in names_seen:
            result.append({
                "precheck_code": pf["key"], "precheck_label": pf["label"],
                "is_required": True, "sort_order": len(result) + 1,
            })
            names_seen.add(pf["key"])

    for sf in supplemental.get(kind, []):
        if sf["key"] not in names_seen:
            result.append({
                "precheck_code": sf["key"], "precheck_label": sf["label"],
                "is_required": True, "sort_order": len(result) + 1,
            })
            names_seen.add(sf["key"])

    return result
