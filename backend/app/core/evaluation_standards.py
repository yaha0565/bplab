"""BPLab Trace LIMS — 十个现有实验评价标准

从 templates/BPLab_十个现有实验评价标准汇总_按记录编号.docx 提取
用于报告判定和结果验证。
"""
from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════
# 评价标准定义
# 每个条目包含: standard(检测标准), criteria(评价指标), limits(限值),
#   judgment(判定原则), validity(有效条件)
# ═══════════════════════════════════════════════════════════════

EVALUATION_STANDARDS: dict[str, dict[str, Any]] = {
    # ── R001: 表面粗糙度试验 ──
    "R001": {
        "experiment_name": "表面粗糙度试验",
        "kind": "rough",
        "standard": "YY/T 1702",
        "criteria": [
            "轮廓算术平均偏差 Ra",
        ],
        "limits": {
            "Ra": "每条测量线 Ra 平均值均 ≤ 15 μm",
            "Ra_max": 15.0,  # μm
        },
        "judgment": "3条测量线 Ra 平均值均满足限值 → 符合；任一条不满足 → 不符合",
        "validity_conditions": [
            "测量前使用标准粗糙度样板校准仪器",
            "每试样至少3条测量线，每条测量线取样长度和评定长度符合标准",
            "Ra值应在仪器有效量程内",
        ],
    },

    # ── R004: 金属-陶瓷结合裂纹萌生试验 ──
    "R004": {
        "experiment_name": "金属-陶瓷结合裂纹萌生试验",
        "kind": "mc_crack",
        "standard": "YY 0621.1",
        "criteria": [
            "金属—陶瓷结合强度 τb",
        ],
        "limits": {
            "tau_b": "τb > 25 MPa",
            "tau_b_min": 25.0,  # MPa
        },
        "judgment": "τb > 25 MPa → 符合；τb ≤ 25 MPa → 不符合",
        "validity_conditions": [
            "试验加载速率符合标准规定",
            "夹具对中良好，无偏心载荷",
            "试样制备符合标准尺寸要求",
            "断裂模式为界面断裂（非内聚断裂）有效",
        ],
    },

    # ── R005: 金属内部质量X射线灰度分析 ──
    "R005": {
        "experiment_name": "金属内部质量X射线灰度分析",
        "kind": "xray",
        "standard": "GB 17168",
        "criteria": [
            "X射线图像质量",
            "内部缺陷判定",
        ],
        "limits": {
            "image_quality": "像质计显示清晰，无影响判定的异常影像",
            "defects": "按委托/产品技术要求",
        },
        "judgment": "图像有效且符合缺陷限值 → 符合；图像无效或存在超标缺陷 → 不符合",
        "validity_conditions": [
            "像质计灵敏度符合标准要求",
            "透照参数（电压、电流、时间）符合工艺规程",
            "底片/数字图像无伪影干扰",
        ],
    },

    # ── R006: 翘曲变形试验 ──
    "R006": {
        "experiment_name": "翘曲变形试验",
        "kind": "warp",
        "standard": "YY/T 1702",
        "criteria": [
            "翘曲变化量 ΔH",
        ],
        "limits": {
            "delta_h": "|ΔH| ≤ 0.5 mm（或按委托/产品技术要求）",
            "delta_h_default": 0.5,  # mm
        },
        "judgment": "|ΔH| ≤ 限值 → 符合；|ΔH| > 限值 → 不符合",
        "validity_conditions": [
            "测量前试样在标准环境下充分平衡",
            "测量基准面平整度符合要求",
            "多点测量取最大值",
        ],
    },

    # ── R007: 热膨胀系数试验 ──
    "R007": {
        "experiment_name": "热膨胀系数试验",
        "kind": "cte",
        "standard": "YY 0621.1",
        "criteria": [
            "线膨胀系数 α（规定温度区间）",
        ],
        "limits": {
            "alpha": "按委托/产品技术要求判定",
        },
        "judgment": "实测值在委托要求范围内 → 符合；否则 → 不符合",
        "validity_conditions": [
            "温度校准在有效期内",
            "升温速率符合标准",
            "试样长度和端面平整度符合要求",
        ],
    },

    # ── R009: 陶瓷牙耐急冷急热试验 ──
    "R009": {
        "experiment_name": "陶瓷牙耐急冷急热试验",
        "kind": "shock",
        "standard": "YY 0300",
        "criteria": [
            "试样完整性（裂纹、崩瓷、破裂）",
        ],
        "limits": {
            "integrity": "全部样品经试验后应无裂纹、崩瓷或破裂",
        },
        "judgment": "全部样品无裂纹、崩瓷、破裂 → 符合；任一样品出现上述缺陷 → 不符合",
        "validity_conditions": [
            "冷热循环温度和时间符合标准",
            "转换时间在规定范围内",
            "目视或低倍放大检查充分",
        ],
    },

    # ── R010: 弯曲性能试验 ──
    "R010": {
        "experiment_name": "弯曲性能试验",
        "kind": "bend",
        "standard": "YY/T 1702",
        "criteria": [
            "0.2% 规定非比例弯曲应力 σ0.2",
        ],
        "limits": {
            "sigma_0_2": "σ0.2 ≥ 800 MPa（或按委托/产品技术要求）",
            "sigma_0_2_default": 800.0,  # MPa
        },
        "judgment": "σ0.2 ≥ 限值 → 符合；σ0.2 < 限值 → 不符合",
        "validity_conditions": [
            "跨距和加载速率符合标准",
            "试样尺寸测量精确",
            "载荷-位移曲线记录完整",
        ],
    },

    # ── R011: 维氏硬度试验 ──
    "R011": {
        "experiment_name": "维氏硬度试验",
        "kind": "hv",
        "standard": "GB/T 4340.1",
        "criteria": [
            "维氏硬度 HV10",
        ],
        "limits": {
            "hv": "按委托/产品技术要求进行符合性判定",
        },
        "judgment": "报告实测 HV10 结果，按委托要求判定",
        "validity_conditions": [
            "硬度计在检定/校准有效期内",
            "试验力选择正确（HV10）",
            "压痕对角线测量精确",
            "试样表面制备符合标准",
        ],
    },

    # ── R012: 牙科材料色稳定性试验 ──
    "R012": {
        "experiment_name": "牙科材料色稳定性试验",
        "kind": "color",
        "standard": "YY 0710",
        "criteria": [
            "照射区与未照射区色泽差异",
        ],
        "limits": {
            "color_diff": "规定条件照射 24h 后，照射区与未照射区不得出现明显色泽差异",
        },
        "judgment": "无明显色泽差异 → 符合；明显差异 → 不符合",
        "validity_conditions": [
            "照射光源和辐照度符合标准",
            "照射时间精确控制",
            "色差评价在标准光源下进行",
            "未照射区对照有效",
        ],
    },

    # ── R013: 增材制造金属试样厚度测量 ──
    "R013": {
        "experiment_name": "增材制造金属试样厚度测量",
        "kind": "thickness",
        "standard": "YY/T 1702",
        "criteria": [
            "平均厚度相对设计厚度偏差",
        ],
        "limits": {
            "thickness_deviation": "各试样平均厚度相对设计厚度偏差应在 ±0.05 mm 内",
            "thickness_tolerance": 0.05,  # mm
        },
        "judgment": "所有试样偏差在 ±0.05 mm 内 → 符合；任一试样偏差超出 → 不符合",
        "validity_conditions": [
            "量具在检定/校准有效期内",
            "多点测量取平均值",
            "设计厚度明确记录",
        ],
    },

    # ── R014: 定制式固定义齿综合检验 ──
    "R014": {
        "experiment_name": "定制式固定义齿综合检验",
        "kind": "fixed_denture",
        "standard": "YY/T 1936-2024",
        "criteria": [
            "资料审查",
            "外观检验",
            "适合性检验",
            "尺寸检验",
            "粗糙度检验",
            "孔隙度检验",
        ],
        "limits": {
            "overall": "按 YY/T 1936-2024 完成适用的综合检验",
        },
        "judgment": "所有适用项目合格 → 符合；任一项不合格 → 不符合",
        "validity_conditions": [
            "检验项目根据委托/产品类型确定",
            "各检验项目执行标准对应章节的方法",
            "原始记录完整可追溯",
        ],
    },

    # ── R015: 定制式活动义齿综合检验 ──
    "R015": {
        "experiment_name": "定制式活动义齿综合检验",
        "kind": "removable_denture",
        "standard": "YY/T 1937-2024",
        "criteria": [
            "资料审查",
            "模型检验",
            "外观检验",
            "适合性检验",
            "厚度测量",
            "内部质量",
            "孔隙度检验",
        ],
        "limits": {
            "overall": "按 YY/T 1937-2024 及当前无色稳定性删减版 SOP 完成综合检验",
        },
        "judgment": "所有适用项目合格 → 符合；任一项不合格 → 不符合",
        "validity_conditions": [
            "检验项目根据委托/产品类型确定",
            "各检验项目执行标准对应章节的方法",
            "原始记录完整可追溯",
        ],
    },
}


def get_standard(kind: str) -> dict[str, Any] | None:
    """根据实验 kind 获取评价标准"""
    # 反向查找 kind → template code
    kind_to_code = {
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
    code = kind_to_code.get(kind)
    return EVALUATION_STANDARDS.get(code) if code else None


def get_standard_by_code(record_template_code: str) -> dict[str, Any] | None:
    """根据记录模板编号获取评价标准"""
    return EVALUATION_STANDARDS.get(record_template_code)


def get_requirement_text(kind: str) -> str:
    """获取评价要求的文本描述"""
    std = get_standard(kind)
    if std and std.get("limits"):
        # 取第一个限值描述
        limits = std["limits"]
        for key, value in limits.items():
            if isinstance(value, str):
                return value
    return "按委托/产品技术要求。"


def validate_result(kind: str, result_values: dict[str, float]) -> tuple[bool, str]:
    """验证实验结果是否符合评价标准。

    Args:
        kind: 实验类型
        result_values: 测量结果值字典

    Returns:
        (符合/不符合, 判定说明)
    """
    std = get_standard(kind)
    if not std:
        return True, "无评价标准，仅报告实测结果"

    limits = std.get("limits", {})

    if kind == "rough":
        ra = result_values.get("Ra", result_values.get("avg", 999))
        passed = ra <= limits.get("Ra_max", 15.0)
        return passed, f"Ra={ra:.3f} μm, 限值≤{limits.get('Ra_max', 15.0)} μm"

    elif kind == "mc_crack":
        tau = result_values.get("tau_b", 0)
        passed = tau > limits.get("tau_b_min", 25.0)
        return passed, f"τb={tau:.2f} MPa, 限值>{limits.get('tau_b_min', 25.0)} MPa"

    elif kind == "warp":
        dh = abs(result_values.get("delta_h", 999))
        limit = limits.get("delta_h_default", 0.5)
        passed = dh <= limit
        return passed, f"|ΔH|={dh:.3f} mm, 限值≤{limit} mm"

    elif kind == "bend":
        sigma = result_values.get("sigma_0_2", 0)
        limit = limits.get("sigma_0_2_default", 800.0)
        passed = sigma >= limit
        return passed, f"σ0.2={sigma:.1f} MPa, 限值≥{limit} MPa"

    elif kind == "thickness":
        dev = abs(result_values.get("deviation", 999))
        tol = limits.get("thickness_tolerance", 0.05)
        passed = dev <= tol
        return passed, f"偏差={dev:.4f} mm, 限值≤{tol} mm"

    elif kind == "shock":
        defect_count = result_values.get("defect_count", 0)
        passed = defect_count == 0
        return passed, "无裂纹/崩瓷/破裂" if passed else f"发现{defect_count}处缺陷"

    # 其他类型：仅报告结果，不做自动判定
    return True, "按委托/产品技术要求判定（需人工确认）"
