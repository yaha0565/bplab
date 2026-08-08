"""BPLab Trace LIMS — 编号与命名规则

从 templates/7.29_BPLab_Trace编号与命名规则汇总_修改版.docx 提取
整合到系统编号生成逻辑中。
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

# 中国标准时间 (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))


def china_now() -> datetime:
    """返回当前北京时间（带时区）"""
    return datetime.now(CHINA_TZ)


def china_today() -> date:
    """返回当前北京日期"""
    return china_now().date()


# ═══════════════════════════════════════════════════════════════
# 1. 编号规则 — 格式定义
# ═══════════════════════════════════════════════════════════════

# 委托编号: WT + YYYYMMDD + NNN (3位序号，按日重置)
COMMISSION_PREFIX = "WT"
COMMISSION_PATTERN = r"^WT\d{11}$"  # WT + 8位日期 + 3位序号 = 13位
COMMISSION_FORMAT = "WT{date}{seq:03d}"

# 样品组编号: BP + YYYYMMDD + NNN (3位序号，按日重置)
SAMPLE_GROUP_PREFIX = "BP"
SAMPLE_GROUP_PATTERN = r"^BP\d{11}$"  # BP + 8位日期 + 3位序号 = 13位
SAMPLE_GROUP_FORMAT = "BP{date}{seq:03d}"

# 实验样品编号: {GroupNo}-S{NN} (2位序号)
SAMPLE_SUFFIX = "-S{seq:02d}"
SAMPLE_PATTERN = r"^BP\d{11}-S\d{2}$"

# 实验任务编号: {GroupNo}-T{NN} (2位序号)
TASK_SUFFIX = "-T{seq:02d}"
TASK_PATTERN = r"^BP\d{11}-T\d{2}$"

# 原始记录编号: 同任务编号
RECORD_NO_IS_TASK_NO = True

# 检验报告编号: R + YYYYMMDD + NNN - T{NN}
REPORT_PREFIX = "R"
REPORT_FORMAT = "R{date}{seq:03d}-T{task_seq:02d}"
REPORT_PATTERN = r"^R\d{11}-T\d{2}$"

# 报告发放登记单编号: 报告编号 + -D
REPORT_DELIVERY_SUFFIX = "-D"

# 客户异议单编号: Y + YYYYMMDD + NNN
OBJECTION_PREFIX = "Y"
OBJECTION_FORMAT = "Y{date}{seq:03d}"
OBJECTION_PATTERN = r"^Y\d{11}$"

# 异议答复函编号: 异议单号 + -R
OBJECTION_RESPONSE_SUFFIX = "-R"

# 危废处置登记表编号: D + YYYYMMDD + NNN
HAZARDOUS_WASTE_PREFIX = "D"
HAZARDOUS_WASTE_FORMAT = "D{date}{seq:03d}"
HAZARDOUS_WASTE_PATTERN = r"^D\d{11}$"


# ═══════════════════════════════════════════════════════════════
# 2. 样品命名规范
# ═══════════════════════════════════════════════════════════════

# 样品类型代码
SAMPLE_TYPE_CODES = {
    "SY": "试样",     # Shi Yang
    "GD": "固定",     # Gu Ding — 固定修复体
    "HD": "活动",     # Huo Dong — 活动修复体
    "QT": "其他",     # Qi Ta
}

# 材料缩写 → 材料名称
MATERIAL_ABBREVIATIONS = {
    "CC": "尺寸",
    "NF": "耐腐",
    "KH": "抗滑",
    "LS": "拉伸",
    "TX": "弹性",
    "WQ": "弯曲",
    "BM": "表面",
    "XZ": "形状",
    "JC": "接触",
    "BL": "剥离",
    "CT": "传统/瓷陶",
    "FH": "复合",
    "GG": "钴铬",
    "JM": "精密/界面",
    "NG": "镍铬/凝固",
    "SZ": "树脂",
    "TH": "钛合金",
    "YH": "氧化锆",
    "ZC": "铸瓷/支撑",
}

# 样品命名格式: {Type}-{Material_Abbr}-{Sequence}-{Material_Suffix}
# 示例: SY-CC-01-1
SAMPLE_NAME_FORMAT = "{sample_type}-{material_abbr}-{sequence}-{material_suffix}"


def build_sample_name(
    sample_type: str = "SY",
    material_abbr: str = "TH",
    sequence: str | int = 1,
    material_suffix: str = "1",
) -> str:
    """根据命名规范生成样品名称。

    Args:
        sample_type: 样品类型 (SY/GD/HD/QT)
        material_abbr: 材料缩写 (见 MATERIAL_ABBREVIATIONS)
        sequence: 序号
        material_suffix: 牌号后缀
    """
    seq_str = str(sequence).zfill(2) if isinstance(sequence, int) else sequence
    return SAMPLE_NAME_FORMAT.format(
        sample_type=sample_type,
        material_abbr=material_abbr,
        sequence=seq_str,
        material_suffix=material_suffix,
    )


# ═══════════════════════════════════════════════════════════════
# 3. 原始记录模板编号 (R001-R013)
# ═══════════════════════════════════════════════════════════════

RECORD_TEMPLATE_CODES = {
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

# 实验 kind → 记录模板编号
KIND_TO_TEMPLATE = {
    "rough": "R001",
    "mc_crack": "R004",
    "xray": "R005",
    "warp": "R006",
    "cte": "R007",
    "shock": "R009",
    "bend": "R010",
    "hv": "R011",
    "color": "R012",
    "thickness": "R013",
    "fixed_denture": "R014",
    "removable_denture": "R015",
}


# ═══════════════════════════════════════════════════════════════
# 4. 拍照命名规范
# ═══════════════════════════════════════════════════════════════

PHOTO_CHECKPOINT_CODES = {
    "ENV": "环境照片",
    "SAMPLE_BEFORE": "实验前样品照片",
    "SAMPLE_AFTER": "实验后样品照片",
    "DEVICE": "设备照片",
    "PROCESS": "过程照片",
    "ABNORMAL": "异常/偏离照片",
    "REFERENCE": "参考标准照片",
    "OTHER": "其他补充照片",
}

# 照片命名格式: {TaskNo}_{CheckpointCode}_{SampleNo}_{Timestamp}.jpg
PHOTO_NAME_FORMAT = "{task_no}_{checkpoint}_{sample_no}_{timestamp}.jpg"


# ═══════════════════════════════════════════════════════════════
# 5. 编号生成工具函数
# ═══════════════════════════════════════════════════════════════

def generate_commission_no(date_str: str, seq: int) -> str:
    """生成委托编号: WT + YYYYMMDD + 3位序号"""
    date_part = date_str.replace("-", "")
    return COMMISSION_FORMAT.format(date=date_part, seq=seq)


def generate_sample_group_no(date_str: str, seq: int) -> str:
    """生成样品组编号: BP + YYYYMMDD + 3位序号"""
    date_part = date_str.replace("-", "")
    return SAMPLE_GROUP_FORMAT.format(date=date_part, seq=seq)


def generate_sample_no(group_no: str, seq: int) -> str:
    """生成实验样品编号: GroupNo-S{NN}"""
    return f"{group_no}{SAMPLE_SUFFIX.format(seq=seq)}"


def generate_task_no(group_no: str, seq: int) -> str:
    """生成实验任务编号: GroupNo-T{NN}"""
    return f"{group_no}{TASK_SUFFIX.format(seq=seq)}"


def generate_report_no(date_str: str, seq: int, task_seq: int) -> str:
    """生成检验报告编号: R + YYYYMMDD + NNN - T{NN}"""
    date_part = date_str.replace("-", "")
    return REPORT_FORMAT.format(date=date_part, seq=seq, task_seq=task_seq)


def generate_objection_no(date_str: str, seq: int) -> str:
    """生成客户异议单编号: Y + YYYYMMDD + NNN"""
    date_part = date_str.replace("-", "")
    return OBJECTION_FORMAT.format(date=date_part, seq=seq)


def generate_hazardous_waste_no(date_str: str, seq: int) -> str:
    """生成危废处置登记表编号: D + YYYYMMDD + NNN"""
    date_part = date_str.replace("-", "")
    return HAZARDOUS_WASTE_FORMAT.format(date=date_part, seq=seq)


def template_code_for_kind(kind: str) -> str:
    """根据实验 kind 获取记录模板编号"""
    return KIND_TO_TEMPLATE.get(kind, "R000")


def validate_commission_no(no: str) -> bool:
    """校验委托编号格式"""
    import re
    return bool(re.match(COMMISSION_PATTERN, no))


def validate_sample_group_no(no: str) -> bool:
    """校验样品组编号格式"""
    import re
    return bool(re.match(SAMPLE_GROUP_PATTERN, no))
