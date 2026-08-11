"""实验配置硬编码默认值 — 安全网回退 (对齐 streamlit-legacy V9.4.2)

字段类型: text / number / select / multiselect / checkbox / date / datetime / textarea
新实验只需在 experiment_methods 表添加记录 + 创建 config 版本即可运行，不必改代码。

actual=True  → "本次核查与实际记录"（实验员必须填写）
actual=False/不设 → "固定参数"（有默认值，可按受控方法执行）
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════
# 共享字段块
# ═══════════════════════════════════════════════════════════════

COMMON_ENV_FIELDS = [
    {"key": "test_date", "label": "检测日期", "type": "date"},
    {"key": "temperature_before", "label": "检测前温度/℃", "type": "number", "default": 23.0, "actual": True},
    {"key": "temperature_after", "label": "检测后温度/℃", "type": "number", "default": 23.0, "actual": True},
    {"key": "humidity_before", "label": "检测前湿度/%RH", "type": "number", "default": 50.0, "actual": True},
    {"key": "humidity_after", "label": "检测后湿度/%RH", "type": "number", "default": 50.0, "actual": True},
    {"key": "detection_location", "label": "检测地点", "type": "text", "readonly": True},
    {"key": "start_time", "label": "实验开始时间", "type": "datetime", "actual": True},
    {"key": "end_time", "label": "实验结束时间", "type": "datetime", "actual": True},
    {"key": "environment_interference", "label": "振动/气流影响", "type": "select", "options": ["无明显干扰", "有干扰"], "default": "无明显干扰"},
    {"key": "work_area_status", "label": "试验区域状态", "type": "multiselect", "options": ["清洁", "干燥", "无明显粉尘", "无无关物品"], "default": ["清洁", "干燥", "无明显粉尘", "无无关物品"]},
    {"key": "software", "label": "软件名称/版本", "type": "text"},
    {"key": "data_path", "label": "仪器原始数据保存路径", "type": "text"},
]

COMMON_DEVICE_FIELDS = [
    {"key": "equipment_name", "label": "主要设备名称", "type": "text", "readonly": True},
    {"key": "equipment_model", "label": "设备型号/规格", "type": "text", "readonly": True},
    {"key": "equipment_no", "label": "设备管理编号", "type": "text", "readonly": True},
    {"key": "calibration_certificate", "label": "校准/检定证书编号", "type": "text", "readonly": True},
    {"key": "calibration_due", "label": "台账校准时间", "type": "text", "readonly": True},
    {"key": "equipment_status", "label": "使用前设备状态", "type": "select", "options": ["正常", "异常"]},
]

# ── 通用母版过程确认（所有实验共用）──
COMMON_PROCESS_OBSERVATIONS = [
    {"key": "temperature_compliance", "label": "本次温度条件是否符合", "type": "select",
     "options": ["符合", "不符合"], "default": "符合", "actual": True},
    {"key": "humidity_compliance", "label": "本次湿度条件是否符合", "type": "select",
     "options": ["符合", "不符合"], "default": "符合", "actual": True},
    {"key": "interference_compliance", "label": "环境干扰控制是否符合", "type": "select",
     "options": ["符合", "不符合"], "default": "符合", "actual": True},
    {"key": "work_area_condition", "label": "工作区域实际状态", "type": "multiselect",
     "options": ["清洁", "干燥", "无明显粉尘", "无无关物品"],
     "default": ["清洁", "干燥", "无明显粉尘", "无无关物品"], "actual": True},
    {"key": "equipment_traceability_confirmation", "label": "设备证书、有效期及溯源信息核对结果",
     "type": "select", "options": ["已核对且在有效期内", "存在异常"], "default": "已核对且在有效期内", "actual": True},
    {"key": "sample_production_date", "label": "样品生产日期/批次日期", "type": "text",
     "default": "委托资料未提供", "actual": True},
    {"key": "sample_preparation_actual", "label": "本次样品制备及表面状态说明", "type": "text",
     "default": "已按方法要求确认", "actual": True},
    {"key": "method_execution_confirmation", "label": "本次操作与受控方法一致性",
     "type": "select", "options": ["一致", "存在偏离"], "default": "一致", "actual": True},
]

# ── 各实验专属补充观察字段 ──
SUPPLEMENTAL_PROCESS_FIELDS = {
    "rough": [
        {"key": "z_axis_marking", "label": "Z轴正方向标识", "type": "select",
         "options": ["清晰", "不清晰"], "default": "清晰", "actual": True},
        {"key": "surface_cleaning_actual", "label": "测试面清洁状态", "type": "select",
         "options": ["清洁", "不清洁"], "default": "清洁", "actual": True},
        {"key": "fixture_stability", "label": "试样固定及工作台稳定性", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "measurement_line_note", "label": "实际测量线/方向说明", "type": "text",
         "default": "按受控方法规定位置测量", "actual": True},
    ],
    "mc_crack": [
        {"key": "centering_confirmation", "label": "试样居中及跨距确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "crack_observation_note", "label": "裂纹萌生/陶瓷剥离观察说明", "type": "text",
         "default": "按声响或目视结果判定", "actual": True},
    ],
    "xray": [
        {"key": "sample_surface_xray", "label": "样品表面清洁、干燥状态", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "radiation_zone_clear", "label": "辐射区域无无关人员及物品", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "panel_iqi_position_confirmation", "label": "探测板、像质计与样品位置确认",
         "type": "select", "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "operator_authorization", "label": "X射线操作授权确认", "type": "select",
         "options": ["已授权", "未授权"], "default": "已授权", "actual": True},
        {"key": "density_control_note", "label": "密度/灰度标准控制范围及核查说明", "type": "text",
         "default": "核查结果在受控范围内", "actual": True},
    ],
    "warp": [
        {"key": "baseline_actual", "label": "切割前基准线实际确认", "type": "select",
         "options": ["清晰且符合", "不符合"], "default": "清晰且符合", "actual": True},
        {"key": "cutting_position_note", "label": "实际切割位置及方向说明", "type": "text",
         "default": "按受控方法规定位置和方向切割", "actual": True},
        {"key": "coolant_actual", "label": "切割过程冷却液状态", "type": "select",
         "options": ["持续供给", "异常"], "default": "持续供给", "actual": True},
    ],
    "cte": [
        {"key": "specimen_processing_state", "label": "试样加工及端面状态", "type": "text",
         "default": "尺寸及端面状态满足方法要求", "actual": True},
        {"key": "baseline_stability_actual", "label": "启动前基线/PV稳定性", "type": "select",
         "options": ["稳定", "不稳定"], "default": "稳定", "actual": True},
        {"key": "program_execution_note", "label": "升温程序实际执行确认", "type": "text",
         "default": "按设定程序完整执行", "actual": True},
    ],
    "shock": [
        {"key": "initial_appearance_actual", "label": "试验前逐件外观状态", "type": "text",
         "default": "逐件检查未见裂纹、崩瓷或破损", "actual": True},
        {"key": "transfer_compliance", "label": "热冷转移时间与浸没状态", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "inspection_condition", "label": "观察照度、放大条件及冷却状态",
         "type": "select", "options": ["符合", "不符合"], "default": "符合", "actual": True},
    ],
    "bend": [
        {"key": "specimen_direction", "label": "试样/打印方向", "type": "text",
         "default": "已按委托及方法要求确认", "actual": True},
        {"key": "fixture_centering", "label": "夹具平行、试样居中及紧固确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "zero_and_contact", "label": "力值调零及挠度计接触确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
    ],
    "hv": [
        {"key": "surface_preparation_hv", "label": "测试面磨制/抛光及清洁状态", "type": "text",
         "default": "表面平整清洁且不影响压痕", "actual": True},
        {"key": "software_version_actual", "label": "本次硬度测量软件版本", "type": "text",
         "default": "由设备配置核对", "actual": True},
        {"key": "loading_unloading_confirmation", "label": "加载、保荷及卸载过程", "type": "select",
         "options": ["正常", "异常"], "default": "正常", "actual": True},
    ],
    "thickness": [
        {"key": "design_file_no", "label": "设计文件/图纸编号", "type": "text",
         "default": "委托资料未提供", "actual": True},
        {"key": "fixture_method_note", "label": "固定方式、测点布置及重复测量说明", "type": "text",
         "default": "固定端/中点/自由端各测3点并重复3次", "actual": True},
    ],
    "color": [
        {"key": "control_sample_confirmation", "label": "对照试样及编号确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "observer_identity_note", "label": "三名观察者身份及资格记录", "type": "text",
         "default": "已核对三名观察者身份及颜色视觉资格", "actual": True},
        {"key": "d65_environment_ready", "label": "D65灯箱、背景及观察环境", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "lamp_filter_service_note", "label": "光源/滤光片编号及使用时间核对", "type": "text",
         "default": "已核对且在受控使用范围内", "actual": True},
        {"key": "sample_position_note", "label": "试样位置、遮盖及水位说明", "type": "text",
         "default": "位置、遮盖和水位符合方法要求", "actual": True},
    ],
    "density": [
        {"key": "cleaning_confirmation", "label": "试样清洗状态确认", "type": "select",
         "options": ["已清洗", "未清洗"], "default": "已清洗", "actual": True},
        {"key": "buoyancy_medium_note", "label": "浸没介质（纯水）状态说明", "type": "text",
         "default": "纯水温度已稳定至23±0.2℃", "actual": True},
        {"key": "balance_zero_check", "label": "天平调零及稳定确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "bubble_check", "label": "试样浸没气泡附着检查", "type": "select",
         "options": ["无气泡", "有气泡"], "default": "无气泡", "actual": True},
        {"key": "standard_block_verification", "label": "标准密度块/参考标准核查", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
    ],
    "tarnish": [
        {"key": "solution_freshness", "label": "硫化钠溶液新鲜度及保存状态", "type": "select",
         "options": ["新鲜配制", "保存期内"], "default": "新鲜配制", "actual": True},
        {"key": "ph_verification", "label": "溶液pH确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "immersion_cycle_note", "label": "交替浸没循环状态确认", "type": "text",
         "default": "10-15次/min交替浸没，运转正常", "actual": True},
        {"key": "observation_lighting", "label": "观察光源及照度确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "observer_qualification", "label": "三名观察者资格确认", "type": "select",
         "options": ["符合", "不符合"], "default": "符合", "actual": True},
        {"key": "temperature_stability", "label": "恒温控制确认", "type": "select",
         "options": ["稳定", "波动超限"], "default": "稳定", "actual": True},
    ],
}

# ── 动态字段生成器 ──

XRAY_IQI_RAW_FIELDS = [
    {
        "key": f"iqi_gray_{point:02d}_{reading}",
        "label": f"像质计{point / 10:.1f} mm灰度·第{reading}次",
        "type": "number",
        "actual": True,
    }
    for point in range(1, 11)
    for reading in range(1, 4)
]

SHOCK_MONITOR_FIELDS = [
    field
    for point, label in enumerate(("试验前", "样品入水前", "样品入水15s", "样品入水30s", "样品入烘箱后"), 1)
    for field in (
        {"key": f"monitor_{point}_time", "label": f"{label}·测量时间", "type": "text", "actual": True},
        {"key": f"monitor_{point}_temperature", "label": f"{label}·冰水温度/℃", "type": "number", "default": 1.0, "actual": True},
        {"key": f"monitor_{point}_stable", "label": f"{label}·稳定读数≥30s", "type": "select", "options": ["是", "否"], "default": "是"},
        {"key": f"monitor_{point}_status", "label": f"{label}·处理状态", "type": "select", "options": ["符合", "偏离"], "default": "符合"},
        {"key": f"monitor_{point}_note", "label": f"{label}·处理措施/备注", "type": "text", "actual": True},
    )
]

COLOR_MONITOR_FIELDS = [
    field
    for point, label, runtime in (
        (1, "开始", 0.0), (2, "过程1", 4.0), (3, "过程2", 8.0),
        (4, "过程3", 12.0), (5, "过程4", 20.0), (6, "结束", 24.0),
    )
    for field in (
        {"key": f"color_monitor_{point}_datetime", "label": f"{label}·日期/时间", "type": "datetime", "actual": True},
        {"key": f"color_monitor_{point}_runtime", "label": f"{label}·累计时间/h", "type": "number", "default": runtime, "actual": True},
        {"key": f"color_monitor_{point}_water_temperature", "label": f"{label}·水浴温度/℃", "type": "number", "default": 37.0, "actual": True},
        {"key": f"color_monitor_{point}_illuminance", "label": f"{label}·试样表面照度/lx", "type": "number", "default": 150000.0, "actual": True},
        {"key": f"color_monitor_{point}_distance", "label": f"{label}·水面距离/mm", "type": "number", "default": 10.0, "actual": True},
        {"key": f"color_monitor_{point}_device_status", "label": f"{label}·设备状态", "type": "select", "options": ["正常", "异常"], "default": "正常"},
        {"key": f"color_monitor_{point}_sample_status", "label": f"{label}·试样/遮盖状态", "type": "select", "options": ["正常", "异常"], "default": "正常"},
        {"key": f"color_monitor_{point}_note", "label": f"{label}·备注", "type": "text", "actual": True},
    )
]

# ═══════════════════════════════════════════════════════════════
# 12 个实验的完整 SCHEMAS（key = experiment_methods.kind）
# ═══════════════════════════════════════════════════════════════

SCHEMAS: dict = {
    # ── I001 / rough — 表面粗糙度试验 ──
    "rough": {
        "title": "表面粗糙度试验",
        "experiment_code": "I001",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "试验参数与使用前确认", "fields": [
                {"key": "standard_block", "label": "标准粗糙度样板编号", "type": "text", "default": "BPGL-B001"},
                {"key": "standard_block_nominal", "label": "标准样板标称值/μm", "type": "number", "default": 3.000},
                {"key": "repeat_check_1", "label": "标准样板实测值1/μm", "type": "number", "actual": True},
                {"key": "repeat_check_2", "label": "标准样板实测值2/μm", "type": "number", "actual": True},
                {"key": "repeat_check_3", "label": "标准样板实测值3/μm", "type": "number", "actual": True},
                {"key": "standard_block_result", "label": "标准样板核查结果", "type": "select", "options": ["合格", "不合格"]},
                {"key": "calculation_standard", "label": "计算标准", "type": "text", "default": "ISO-97"},
                {"key": "shape_removal", "label": "形状去除", "type": "text", "default": "自动"},
                {"key": "filter_type", "label": "滤波器", "type": "text", "default": "高斯"},
                {"key": "lambda_s", "label": "λs", "type": "text", "default": "自动"},
                {"key": "measurement_range", "label": "测量范围/μm", "type": "number", "default": 40.0},
                {"key": "sampling_length", "label": "取样长度/mm", "type": "number", "default": 0.8},
                {"key": "sampling_count", "label": "取样个数", "type": "number", "default": 5.0},
                {"key": "evaluation_length", "label": "评定长度/mm", "type": "number", "default": 4.0},
                {"key": "measuring_speed", "label": "测量速度/mm/s", "type": "number", "default": 0.5},
                {"key": "cutoff_filter", "label": "滤波/计算标准", "type": "text", "default": "高斯"},
                {"key": "probe_condition", "label": "探针状态", "type": "select", "options": ["正常", "异常"]},
                {"key": "platform_level", "label": "工作台水平状态", "type": "select", "options": ["符合", "不符合"]},
                {"key": "surface_state", "label": "试样表面状态", "type": "select", "options": ["原打印表面", "经处理表面", "其他"]},
                {"key": "measurement_direction", "label": "测量方向/线位", "type": "text", "default": "3条平行、不重叠、代表性测量线"},
                {"key": "three_length_mode", "label": "评定长度方式", "type": "select", "options": ["5L（默认）", "3L（已完成方法确认）"], "default": "5L（默认）"},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"),
            ("surface_confirm", "原打印面/方向确认", "select:符合|不符合"),
            ("position", "测量位置", "text"),
            ("ra1", "Ra1/μm", "number"), ("ra2", "Ra2/μm", "number"), ("ra3", "Ra3/μm", "number"),
            ("mean", "平均值/μm", "calc"), ("limit", "判定限值/μm", "number"), ("conclusion", "单样结论", "calc"),
            ("retest_mean", "复测后平均/μm", "number"), ("file_no", "曲线/数据文件编号", "text"), ("note", "备注", "text"),
        ],
    },

    # ── I002 / mc_crack — 金属-陶瓷结合裂纹萌生试验 ──
    "mc_crack": {
        "title": "金属-陶瓷结合裂纹萌生试验",
        "experiment_code": "I002",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "裂纹萌生试验参数", "fields": [
                {"key": "fixture_no", "label": "金瓷结合试验夹具编号", "type": "text", "default": "BPGL-B009"},
                {"key": "support_span", "label": "支承跨距/mm", "type": "number", "default": 20.0},
                {"key": "roller_radius", "label": "压头/支点半径R/mm", "type": "number", "default": 1.0},
                {"key": "parallel_block_no", "label": "平行块编号", "type": "text", "default": "BGGL-B019"},
                {"key": "parallel_block_parallelism", "label": "平行块平行度/mm", "type": "number", "actual": True},
                {"key": "loading_speed", "label": "加载速度/mm/min", "type": "number", "default": 1.5},
                {"key": "observation_method", "label": "裂纹萌生观察方式", "type": "select", "options": ["声响", "目视"], "default": "目视"},
                {"key": "parallel_check", "label": "夹具平行与居中确认", "type": "select", "options": ["符合", "不符合"]},
                {"key": "metal_name", "label": "试样名称", "type": "text", "readonly": True},
                {"key": "metal_batch", "label": "批号", "type": "text", "readonly": True},
                {"key": "em_source", "label": "杨氏模量来源", "type": "select", "options": ["说明书", "检测报告", "注册资料", "质保书", "其他"], "default": "说明书"},
                {"key": "em_source_file", "label": "杨氏模量来源文件编号", "type": "text"},
                {"key": "orientation", "label": "试样放置方向", "type": "select", "options": ["金属面朝上、陶瓷面朝下", "其他"]},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"), ("width", "宽度/mm", "number"),
            ("dm1", "金属厚度1/mm", "number"), ("dm2", "金属厚度2/mm", "number"), ("dm3", "金属厚度3/mm", "number"),
            ("dm_mean", "金属厚度平均/mm", "calc"), ("em", "金属弹性模量/GPa", "number"), ("k", "K/mm⁻²", "number"),
            ("ffail", "裂纹萌生力/N", "number"), ("tau", "结合强度/MPa", "calc"),
            ("crack_position", "开裂位置", "text"), ("failure_mode", "断裂/剥离形态", "text"),
            ("curve_no", "曲线/数据文件编号", "text"),
            ("conclusion", "单样结论", "calc"), ("note", "备注", "text"),
        ],
    },

    # ── I003 / xray — 金属内部质量X射线灰度分析 ──
    "xray": {
        "title": "金属内部质量X射线灰度分析",
        "experiment_code": "I003",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "辐射安全与曝光参数", "fields": [
                {"key": "radiation_safety", "label": "辐射安全确认", "type": "select", "options": ["允许曝光", "禁止曝光"]},
                {"key": "xray_model", "label": "X射线机型号/编号", "type": "text"},
                {"key": "panel_no", "label": "数据采集板编号", "type": "text"},
                {"key": "iqi_no", "label": "孔形像质计编号", "type": "text"},
                {"key": "density_meter_no", "label": "密度计/标准密度片编号", "type": "text"},
                {"key": "density_nominal", "label": "标准密度片标称值", "type": "number", "actual": True},
                {"key": "density_measured_1", "label": "标准密度片实测值1", "type": "number", "actual": True},
                {"key": "density_measured_2", "label": "标准密度片实测值2", "type": "number", "actual": True},
                {"key": "density_measured_3", "label": "标准密度片实测值3", "type": "number", "actual": True},
                {"key": "tube_voltage", "label": "管电压/kV", "type": "number", "default": 75.0},
                {"key": "tube_current", "label": "管电流/mA", "type": "number", "default": 56.0},
                {"key": "exposure_time", "label": "曝光时间/ms", "type": "number", "default": 110.0},
                {"key": "mas", "label": "管电流时间积/mAs", "type": "number", "default": 6.3},
                {"key": "focus_mode", "label": "焦点模式", "type": "text", "default": "L"},
                {"key": "orientation", "label": "样品摆放方向", "type": "text", "default": "咬合面朝下"},
                {"key": "exposure_count", "label": "曝光次数", "type": "number", "default": 1.0},
                {"key": "parameter_adjustment", "label": "参数调整情况", "type": "select", "options": ["无调整", "有调整"], "default": "无调整"},
                *XRAY_IQI_RAW_FIELDS,
                {"key": "image_path", "label": "原始图像保存路径", "type": "text"},
            ]},
        ],
        "columns": [
            ("sample_no", "样品编号", "text"), ("sample_name_tooth", "样品名称/牙位", "text"),
            ("image_no", "图像文件编号", "text"), ("sample_status", "样品状态", "select:完好|异常"),
            ("image_valid", "图像有效性", "select:有效|无效"),
            ("iqi_display", "像质计显示", "select:清晰|不清晰"),
            ("roi1_reading1", "ROI-1灰度·第1次", "number"), ("roi1_reading2", "ROI-1灰度·第2次", "number"), ("roi1_reading3", "ROI-1灰度·第3次", "number"),
            ("roi2_reading1", "ROI-2灰度·第1次", "number"), ("roi2_reading2", "ROI-2灰度·第2次", "number"), ("roi2_reading3", "ROI-2灰度·第3次", "number"),
            ("roi3_reading1", "ROI-3灰度·第1次", "number"), ("roi3_reading2", "ROI-3灰度·第2次", "number"), ("roi3_reading3", "ROI-3灰度·第3次", "number"),
            ("roi1", "ROI-1平均灰度", "calc"), ("roi2", "ROI-2平均灰度", "calc"), ("roi3", "ROI-3平均灰度", "calc"),
            ("roi_mean", "ROI平均灰度", "calc"), ("thickness_relation", "接近/介于像质计厚度点", "text"),
            ("estimated_thickness", "厚度估算结果", "text"), ("defect", "异常影像/位置", "text"),
            ("retake", "是否复拍", "select:否|是"),
            ("conclusion", "单样结论", "select:合格|不合格|需复检|超出适用范围"), ("note", "备注", "text"),
        ],
    },

    # ── I004 / warp — 翘曲变形试验 ──
    "warp": {
        "title": "翘曲变形试验",
        "experiment_code": "I004",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "测量和切割参数", "fields": [
                {"key": "image_device_no", "label": "二次元影像仪编号", "type": "text"},
                {"key": "software_version", "label": "测量软件/版本", "type": "text"},
                {"key": "cutting_device_no", "label": "切割设备编号", "type": "text"},
                {"key": "fixture_no", "label": "专用试样夹具编号", "type": "text"},
                {"key": "cutting_disc", "label": "切割片规格/批号", "type": "text"},
                {"key": "measurement_function", "label": "测量功能", "type": "text", "default": "Point to Line"},
                {"key": "baseline_before", "label": "切割前基准线确认", "type": "select", "options": ["符合", "不符合"]},
                {"key": "coolant", "label": "切割冷却液状态", "type": "select", "options": ["持续供给", "异常"]},
                {"key": "cut_position", "label": "切割位置/方向", "type": "text"},
                {"key": "spindle_speed", "label": "主轴转速实设/显示", "type": "text"},
                {"key": "cutting_stroke", "label": "切割行程", "type": "number", "default": 50.0},
                {"key": "feed_speed", "label": "进给速度", "type": "number", "default": 0.1},
                {"key": "baseline_after", "label": "切割后基准线确认", "type": "select", "options": ["符合", "不符合"]},
                {"key": "image_before_path", "label": "切割前原始图像路径", "type": "text"},
                {"key": "image_after_path", "label": "切割后原始图像路径", "type": "text"},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"), ("h1", "H1/mm", "number"), ("h2", "H2/mm", "number"),
            ("cut_start", "切割开始时间", "text"), ("cut_end", "切割结束时间", "text"),
            ("coolant_status", "冷却液持续供给", "select:是|否"), ("remade", "是否重新制样", "select:否|是"),
            ("delta", "ΔH=H1-H2/mm", "calc"), ("limit", "判定限值/mm", "number"),
            ("edge_condition", "切口崩边/裂纹状态", "text"), ("conclusion", "单样结论", "calc"), ("note", "备注", "text"),
        ],
    },

    # ── I005 / cte — 热膨胀系数试验 ──
    "cte": {
        "title": "热膨胀系数试验",
        "experiment_code": "I005",
        "sections": [
            {"title": "环境与设备", "fields": [
                field for field in COMMON_ENV_FIELDS
                if field["key"] not in {"start_time", "end_time"}
            ] + COMMON_DEVICE_FIELDS},
            {"title": "试验参数", "fields": [
                {"key": "start_temperature", "label": "起始温度/℃", "type": "number", "default": 25.0},
                {"key": "end_temperature", "label": "终止温度/℃", "type": "number", "default": 550.0},
                {"key": "heating_rate", "label": "升温速率/℃·min⁻¹（允许5±1）", "type": "number", "default": 5.0},
                {"key": "sample_processing_state", "label": "制样/处理状态", "type": "select", "options": ["原始状态", "热处理后", "其他"], "default": "原始状态", "actual": True},
                {"key": "pv_range", "label": "PV值/稳定范围", "type": "text", "default": "50～60"},
                {"key": "initial_pv", "label": "试验前PV实测值", "type": "number", "actual": True},
                {"key": "sample_install", "label": "试样安装状态", "type": "select", "options": ["牢固", "异常"]},
                {"key": "curve_path", "label": "热膨胀曲线文件路径", "type": "text"},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"), ("l0", "初始长度L0/mm", "number"),
            ("diameter", "直径/mm", "number"),
            ("installation_direction", "安装方向", "select:正确|不适用"),
            ("sample_secure", "是否牢固", "select:是|否"),
            ("run_status", "升温状态", "select:正常|异常"),
            ("auto_stop", "自动停止", "select:是|否"),
            ("validity", "有效性", "select:有效|无效"),
            ("t1", "起始温度/℃", "number"), ("t2", "终止温度/℃", "number"),
            ("delta_l", "长度变化ΔL/μm", "number"), ("delta_t", "温差ΔT/℃", "calc"),
            ("alpha", "线胀系数/(10⁻⁶/K)", "calc"),
            ("nominal_value", "标称值/(10⁻⁶/K)", "number"),
            ("sample_standard_value", "样品标准值/(10⁻⁶/K)", "number"),
            ("judgement_basis", "判定依据", "text"),
            ("judgement_standard", "判定标准", "text"),
            ("judgement_result", "判定结果", "select:符合|不符合"),
            ("curve_no", "设备数据文件编号", "text"), ("note", "备注", "text"),
        ],
    },

    # ── I006 / shock — 陶瓷牙耐急冷急热试验 ──
    "shock": {
        "title": "陶瓷牙耐急冷急热试验",
        "experiment_code": "I006",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "温度、时间和观察条件", "fields": [
                {"key": "container_no", "label": "金属带孔容器编号", "type": "text", "actual": True},
                {"key": "oven_temperature", "label": "烘箱温度/℃", "type": "number", "default": 100.0},
                {"key": "first_heating_time", "label": "首次加热时间/min", "type": "number", "default": 20.0},
                {"key": "first_heating_start", "label": "首次加热开始时间", "type": "text"},
                {"key": "first_heating_end", "label": "首次加热结束时间", "type": "text"},
                {"key": "transfer_time", "label": "转移时间/s", "type": "number", "default": 3.0},
                {"key": "ice_water_temperature", "label": "冰水温度/℃", "type": "number", "default": 1.0},
                {"key": "immersion_time", "label": "冰水浸泡时间/min", "type": "number", "default": 5.0},
                {"key": "ice_immersion_start", "label": "冰水浸泡开始时间", "type": "text"},
                {"key": "ice_immersion_end", "label": "冰水浸泡结束时间", "type": "text"},
                {"key": "second_heating_time", "label": "再次加热时间/min", "type": "number", "default": 15.0},
                {"key": "second_heating_start", "label": "再次加热开始时间", "type": "text", "actual": True},
                {"key": "second_heating_end", "label": "再次加热结束时间", "type": "text", "actual": True},
                {"key": "cooling_temperature", "label": "观察前冷却温度/℃", "type": "number", "default": 23.0},
                {"key": "illumination", "label": "观察照度/lx", "type": "number", "default": 1000.0},
                {"key": "magnification", "label": "放大倍数", "type": "number", "default": 10.0},
                {"key": "cooling_start", "label": "自然冷却开始时间", "type": "text"},
                {"key": "cooling_end", "label": "自然冷却完成时间", "type": "text"},
                {"key": "surface_temperature", "label": "观察前样品表面温度/℃", "type": "number", "actual": True},
                {"key": "timer_no", "label": "计时器编号", "type": "text"},
                {"key": "thermometer_no", "label": "温度计编号", "type": "text"},
                *SHOCK_MONITOR_FIELDS,
            ]},
        ],
        "columns": [
            ("sample_no", "样品编号/位置", "text"), ("initial_appearance", "初始外观", "select:无异常|有异常"),
            ("crack", "裂纹", "select:无|有"),
            ("chipping", "崩瓷", "select:无|有"), ("fracture", "破裂/裂开", "select:无|有"),
            ("photo_no", "观察照片编号", "text"), ("conclusion", "单样结论", "calc"), ("note", "备注", "text"),
        ],
    },

    # ── I007 / bend — 弯曲性能试验 ──
    "bend": {
        "title": "弯曲性能试验",
        "experiment_code": "I007",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "试样、夹具和软件参数", "fields": [
                {"key": "printing_process", "label": "打印工艺/设备", "type": "text"},
                {"key": "heat_treatment_record", "label": "热处理记录编号", "type": "text"},
                {"key": "printing_direction", "label": "打印方向", "type": "select", "options": ["长轴平行z轴", "长轴垂直z轴（x/y轴）"]},
                {"key": "force_sensor", "label": "2000N力传感器编号", "type": "text"},
                {"key": "sensor_calibration_value", "label": "力传感器校准值/N", "type": "number", "actual": True},
                {"key": "sensor_coefficient", "label": "力传感器校准系数", "type": "number", "actual": True},
                {"key": "deflectometer", "label": "挠度计/变形测量装置编号", "type": "text"},
                {"key": "fixture_no", "label": "三点弯曲夹具编号", "type": "text"},
                {"key": "support_span", "label": "支点距离/mm", "type": "number", "default": 20.0},
                {"key": "speed", "label": "位移速度/mm/min", "type": "number", "default": 1.0},
                {"key": "specified_strain", "label": "规定应变/%", "type": "number", "default": 0.2},
                {"key": "roller_radius", "label": "压头/支点R/mm", "type": "number", "default": 2.0},
                {"key": "fixture_parallel", "label": "上压头/下支撑平行", "type": "select", "options": ["是", "否"]},
                {"key": "max_gap", "label": "平行块/塞尺最大间隙/mm", "type": "number"},
                {"key": "deflectometer_contact", "label": "挠度计状态", "type": "select", "options": ["轻微接触", "预压", "未接触"]},
                {"key": "zero_force", "label": "清零后力值/N", "type": "number"},
                {"key": "start_permission", "label": "开始试验条件", "type": "select", "options": ["可以开始试验", "需调整后再试验"], "default": "可以开始试验"},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"), ("length", "长度/mm", "number"), ("width", "宽度/mm", "number"),
            ("height", "高度/mm", "number"), ("span", "支点距/mm", "number"), ("speed", "速度/mm/min", "number"),
            ("fmax", "Fmax/N", "number"), ("stress_02", "0.2%规定非比例弯曲应力/MPa", "number"),
            ("curve_no", "曲线/数据文件编号", "text"), ("sample_state", "试样状态", "select:完整|断裂|异常"),
            ("conclusion", "单样结论", "calc"), ("note", "备注", "text"),
        ],
    },

    # ── I008 / hv — 维氏硬度试验 ──
    "hv": {
        "title": "维氏硬度试验",
        "experiment_code": "I008",
        "row_expansion": "faces",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "硬度和试样表面确认", "fields": [
                {"key": "sample_production_date", "label": "样品批号", "type": "text", "readonly": True},
                {"key": "method", "label": "试验力级别", "type": "text", "default": "HV10"},
                {"key": "test_force", "label": "试验力/N", "type": "number", "default": 98.07},
                {"key": "dwell_time", "label": "保荷时间/s", "type": "number", "default": 15.0},
                {"key": "standard_block_no", "label": "标准硬度块编号", "type": "text", "default": "BPGL-B007"},
                {"key": "standard_block_nominal", "label": "标准硬度块标称值/HV", "type": "number", "default": 466.0},
                {"key": "standard_block_due", "label": "标准硬度块有效期", "type": "date"},
                {"key": "standard_block_reading_1", "label": "标准硬度块实测值1/HV", "type": "number", "actual": True},
                {"key": "standard_block_reading_2", "label": "标准硬度块实测值2/HV", "type": "number", "actual": True},
                {"key": "standard_block_reading_3", "label": "标准硬度块实测值3/HV", "type": "number", "actual": True},
                {"key": "standard_block_result", "label": "标准硬度块核查结果", "type": "select", "options": ["合格", "不合格"]},
                {"key": "surface_condition", "label": "测试面状态", "type": "select", "options": ["平整清洁", "异常"]},
                {"key": "perpendicularity", "label": "试样垂直性确认", "type": "select", "options": ["符合", "不符合"]},
                {"key": "indent_measurement_method", "label": "压痕测量方式", "type": "text", "default": "切线测量"},
                {"key": "report_exported", "label": "硬度报告已导出", "type": "select", "options": ["是", "否"], "default": "是"},
            ]},
        ],
        "columns": [
            ("sample_no", "样品编号", "text"), ("face", "测量方向", "text"),
            ("indent1", "压痕1/HV", "number"), ("indent2", "压痕2/HV", "number"), ("indent3", "压痕3/HV", "number"),
            ("mean", "测试面平均/HV", "calc"), ("indent_quality", "压痕有效性", "select:有效|无效"),
            ("image_no", "压痕图像编号", "text"), ("note", "备注", "text"),
        ],
    },

    # ── I009 / thickness — 增材制造金属试样厚度测量 ──
    "thickness": {
        "title": "增材制造金属试样厚度测量",
        "experiment_code": "I009",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "影像测量参数", "fields": [
                {"key": "sample_production_date", "label": "样品批号", "type": "text", "readonly": True},
                {"key": "production_date", "label": "生产日期", "type": "text", "readonly": True},
                {"key": "magnification", "label": "测试放大倍数", "type": "text", "default": "33倍"},
                {"key": "calibration_nominal", "label": "标准量块标称值/mm", "type": "number", "actual": True},
                {"key": "calibration_measured", "label": "标准量块实测值/mm", "type": "number", "actual": True},
                {"key": "calibration_result", "label": "校准核查结果", "type": "select", "options": ["合格", "不合格"]},
                {"key": "preheat_start", "label": "设备预热开始时间", "type": "text"},
                {"key": "preheat_end", "label": "设备预热结束时间", "type": "text"},
                {"key": "measurement_points", "label": "测量点位", "type": "text", "default": "固定端、中点、自由端"},
                {"key": "repeat_count", "label": "每个试样重复测量次数", "type": "number", "default": 3.0},
                {"key": "design_thickness", "label": "设计厚度/mm", "type": "number", "actual": True},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"),
            ("r1_fixed_p1", "重复1·固定端P1/mm", "number"), ("r1_fixed_p2", "重复1·固定端P2/mm", "number"), ("r1_fixed_p3", "重复1·固定端P3/mm", "number"),
            ("r1_middle_p1", "重复1·中点P1/mm", "number"), ("r1_middle_p2", "重复1·中点P2/mm", "number"), ("r1_middle_p3", "重复1·中点P3/mm", "number"),
            ("r1_free_p1", "重复1·自由端P1/mm", "number"), ("r1_free_p2", "重复1·自由端P2/mm", "number"), ("r1_free_p3", "重复1·自由端P3/mm", "number"),
            ("r2_fixed_p1", "重复2·固定端P1/mm", "number"), ("r2_fixed_p2", "重复2·固定端P2/mm", "number"), ("r2_fixed_p3", "重复2·固定端P3/mm", "number"),
            ("r2_middle_p1", "重复2·中点P1/mm", "number"), ("r2_middle_p2", "重复2·中点P2/mm", "number"), ("r2_middle_p3", "重复2·中点P3/mm", "number"),
            ("r2_free_p1", "重复2·自由端P1/mm", "number"), ("r2_free_p2", "重复2·自由端P2/mm", "number"), ("r2_free_p3", "重复2·自由端P3/mm", "number"),
            ("r3_fixed_p1", "重复3·固定端P1/mm", "number"), ("r3_fixed_p2", "重复3·固定端P2/mm", "number"), ("r3_fixed_p3", "重复3·固定端P3/mm", "number"),
            ("r3_middle_p1", "重复3·中点P1/mm", "number"), ("r3_middle_p2", "重复3·中点P2/mm", "number"), ("r3_middle_p3", "重复3·中点P3/mm", "number"),
            ("r3_free_p1", "重复3·自由端P1/mm", "number"), ("r3_free_p2", "重复3·自由端P2/mm", "number"), ("r3_free_p3", "重复3·自由端P3/mm", "number"),
            ("fixed_mean", "固定端总平均/mm", "calc"), ("middle_mean", "中点总平均/mm", "calc"), ("free_mean", "自由端总平均/mm", "calc"),
            ("mean", "试样总平均/mm", "calc"), ("deviation", "尺寸偏差/mm", "calc"), ("limit", "判定要求/mm", "text"),
            ("conclusion", "单样结论", "text"), ("image_no", "图像编号", "text"), ("note", "备注", "text"),
        ],
    },

    # ── I010 / color — 牙科材料色稳定性试验 ──
    "color": {
        "title": "牙科材料色稳定性试验",
        "experiment_code": "I010",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "光照、水浴和观察条件", "fields": [
                {"key": "source_type", "label": "发光源", "type": "select", "options": ["氙灯", "等同光源"]},
                {"key": "lamp_no", "label": "氙灯编号/批号", "type": "text"},
                {"key": "lamp_hours", "label": "氙灯累计使用时间/h", "type": "number"},
                {"key": "filter_no", "label": "滤光片编号/批号", "type": "text"},
                {"key": "filter_hours", "label": "滤光片累计使用时间/h", "type": "number"},
                {"key": "water_temperature", "label": "水浴温度/℃", "type": "number", "default": 37.0},
                {"key": "sample_illuminance", "label": "试样表面照度/lx", "type": "number", "default": 150000.0},
                {"key": "water_distance", "label": "试样与水面距离/mm", "type": "number", "default": 10.0},
                {"key": "exposure_time", "label": "照射时间/h", "type": "number", "default": 24.0},
                {"key": "water_medium", "label": "水浴介质", "type": "select", "options": ["蒸馏水", "去离子水"]},
                {"key": "d65_illuminance", "label": "D65灯箱观察照度/lx", "type": "number", "default": 1500.0},
                {"key": "background", "label": "观察背景板", "type": "select", "options": ["N5中性灰", "白背景+灰背景", "其他"]},
                {"key": "observation_distance", "label": "观察距离/mm", "type": "number", "default": 250.0},
                {"key": "single_observation_time", "label": "单次观察时间/s", "type": "number", "default": 2.0},
                {"key": "observer_1", "label": "观察者1姓名/颜色视觉记录", "type": "text"},
                {"key": "observer_2", "label": "观察者2姓名/颜色视觉记录", "type": "text"},
                {"key": "observer_3", "label": "观察者3姓名/颜色视觉记录", "type": "text"},
                {"key": "observer_qualification", "label": "三名观察者颜色视觉资格", "type": "select", "options": ["均已确认合格", "存在未确认/不合格"], "default": "均已确认合格"},
                {"key": "exposure_start", "label": "照射开始时间", "type": "datetime", "actual": True},
                {"key": "exposure_end", "label": "照射结束时间", "type": "datetime", "actual": True},
                {"key": "water_temperature_end", "label": "结束时水浴温度/℃", "type": "number", "actual": True},
                {"key": "sample_illuminance_end", "label": "结束时试样表面照度/lx", "type": "number", "actual": True},
                {"key": "water_distance_end", "label": "结束时水面距离/mm", "type": "number", "actual": True},
                {"key": "lamp_box_ready", "label": "D65灯箱预热/稳定", "type": "select", "options": ["已完成", "未完成"], "default": "已完成"},
                {"key": "observation_date", "label": "目视观察日期", "type": "date"},
                *COLOR_MONITOR_FIELDS,
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"), ("control_no", "对照试样编号", "text"),
            ("shape", "试样形状", "select:圆片|牙形|其他"), ("size", "试样尺寸", "text"),
            ("cover_method", "遮盖方式", "select:试样夹|锡箔|铝箔"), ("cover_direction", "遮盖区域/方向", "text"),
            ("cover_secure", "遮盖是否牢固", "select:是|否"), ("position", "摆放位置", "text"),
            ("photo_no", "照射前/后照片编号", "text"),
            ("observer1", "观察者1结果", "select:未见明显差异|轻微差异|明显差异|无法判定"),
            ("observer2", "观察者2结果", "select:未见明显差异|轻微差异|明显差异|无法判定"),
            ("observer3", "观察者3结果", "select:未见明显差异|轻微差异|明显差异|无法判定"),
            ("overall", "总体观察结果", "calc"), ("conclusion", "单样结论", "calc"), ("note", "备注", "text"),
        ],
    },

    # ── I011 / fixed_denture — 定制式固定义齿综合检验 ──
    "fixed_denture": {
        "title": "定制式固定义齿综合检验",
        "experiment_code": "I011",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "检验参数", "fields": [
                {"key": "design_no", "label": "设计单编号", "type": "text"},
                {"key": "material", "label": "材料类型", "type": "select", "options": ["氧化锆", "钴铬合金", "纯钛", "二硅酸锂", "其他"], "default": "氧化锆"},
                {"key": "surface_quality", "label": "表面质量", "type": "select", "options": ["合格", "不合格"], "default": "合格"},
                {"key": "margin_fit", "label": "边缘适合性/μm", "type": "number"},
                {"key": "contact_point", "label": "邻接关系", "type": "select", "options": ["合格", "过紧", "过松"], "default": "合格"},
                {"key": "occlusion", "label": "咬合关系", "type": "select", "options": ["合格", "早接触", "无接触"], "default": "合格"},
                {"key": "crown_height", "label": "冠高度/mm", "type": "number"},
                {"key": "crown_width", "label": "冠宽度/mm", "type": "number"},
                {"key": "wall_thickness", "label": "壁厚/mm", "type": "number"},
                {"key": "connector_area", "label": "连接体截面积/mm²", "type": "number"},
            ]},
        ],
        "columns": [
            ("sample_no", "样品编号", "text"),
            ("unit_name", "牙位", "text"),
            ("surface_check", "表面检查", "select:合格|不合格"),
            ("margin_gap", "边缘间隙/μm", "number"),
            ("roughness", "粗糙度Ra/μm", "number"),
            ("porosity", "孔隙度/%", "number"),
            ("conclusion", "单样结论", "calc"),
            ("note", "备注", "text"),
        ],
    },

    # ── I012 / removable_denture — 定制式活动义齿综合检验 ──
    "removable_denture": {
        "title": "定制式活动义齿综合检验",
        "experiment_code": "I012",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "检验参数", "fields": [
                {"key": "design_no", "label": "设计单编号", "type": "text"},
                {"key": "material", "label": "基托材料", "type": "select", "options": ["PMMA", "钴铬合金", "纯钛", "弹性材料", "其他"], "default": "PMMA"},
                {"key": "contour_check", "label": "外形检查", "type": "select", "options": ["合格", "不合格"], "default": "合格"},
                {"key": "adaptation", "label": "适合性", "type": "select", "options": ["合格", "不合格"], "default": "合格"},
                {"key": "retention", "label": "固位力", "type": "select", "options": ["合格", "不足", "过紧"], "default": "合格"},
                {"key": "stability", "label": "稳定性", "type": "select", "options": ["合格", "不合格"], "default": "合格"},
                {"key": "base_thickness", "label": "基托厚度/mm", "type": "number"},
                {"key": "clasp_thickness", "label": "卡环厚度/mm", "type": "number"},
            ]},
        ],
        "columns": [
            ("sample_no", "样品编号", "text"),
            ("check_item", "检查项目", "text"),
            ("result", "结果", "select:合格|不合格"),
            ("conclusion", "单样结论", "calc"),
            ("note", "备注", "text"),
        ],
    },

    # ── I013 / density — 激光选区熔化金属材料密度试验 ──
    "density": {
        "title": "激光选区熔化金属材料密度试验",
        "experiment_code": "I013",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "密度系统与判定依据", "fields": [
                {"key": "balance_internal_calibration", "label": "天平内校准结果", "type": "select", "options": ["合格", "不合格"], "default": "合格"},
                {"key": "density_block_no", "label": "标准密度块/核查样编号", "type": "text", "default": "BPGL-B023"},
                {"key": "system_check_result", "label": "密度系统核查结果", "type": "select", "options": ["合格", "不合格"], "default": "合格"},
                {"key": "auto_calc_check", "label": "自动计算验证", "type": "select", "options": ["一致", "不一致"], "default": "一致"},
                {"key": "water_type", "label": "浸没液", "type": "text", "default": "三级水"},
                {"key": "declared_density", "label": "可追溯声明密度/(g/cm³)", "type": "number", "actual": True},
                {"key": "declared_density_source", "label": "声明密度来源文件", "type": "text", "actual": True},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"),
            ("a1", "测量1空气中质量A/g", "number"), ("b1", "测量1水中表观质量B/g", "number"), ("water_temp1", "测量1水温/℃", "number"), ("water_density1", "测量1水密度/(g/cm³)", "number"), ("auto_density1", "测量1天平密度", "number"), ("density1", "测量1复算密度", "calc"),
            ("a2", "测量2空气中质量A/g", "number"), ("b2", "测量2水中表观质量B/g", "number"), ("water_temp2", "测量2水温/℃", "number"), ("water_density2", "测量2水密度/(g/cm³)", "number"), ("auto_density2", "测量2天平密度", "number"), ("density2", "测量2复算密度", "calc"),
            ("a3", "测量3空气中质量A/g", "number"), ("b3", "测量3水中表观质量B/g", "number"), ("water_temp3", "测量3水温/℃", "number"), ("water_density3", "测量3水密度/(g/cm³)", "number"), ("auto_density3", "测量3天平密度", "number"), ("density3", "测量3复算密度", "calc"),
            ("density_difference", "最大密度差/(g/cm³)", "calc"), ("mean", "平均密度/(g/cm³)", "calc"), ("relative_deviation", "相对偏差/%", "calc"),
            ("conclusion", "单样结论", "calc"), ("data_file_no", "数据文件编号", "text"), ("note", "备注", "text"),
        ],
    },

    # ── I014 / tarnish — 金属材料抗晦暗性能试验 ──
    "tarnish": {
        "title": "金属材料抗晦暗性能试验",
        "experiment_code": "I014",
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS},
            {"title": "溶液、循环与观察条件", "fields": [
                {"key": "immersion_device_no", "label": "循环浸泡仪管理编号", "type": "text", "default": "BPGL-A043"},
                {"key": "solution_concentration", "label": "硫化钠溶液浓度/(mol/L)", "type": "number", "default": 0.1},
                {"key": "solution_mass_initial", "label": "初始批Na₂S·9H₂O称量/g", "type": "number", "default": 22.3, "actual": True},
                {"key": "solution_mass_24h", "label": "24 h批称量/g", "type": "number", "default": 22.3, "actual": True},
                {"key": "solution_mass_48h", "label": "48 h批称量/g", "type": "number", "default": 22.3, "actual": True},
                {"key": "bath_temperature", "label": "试验温度/℃", "type": "number", "default": 23.0, "actual": True},
                {"key": "cycle_immersion_seconds", "label": "每分钟浸泡时间/s", "type": "number", "default": 12.5, "actual": True},
                {"key": "total_duration", "label": "总试验时间/h", "type": "number", "default": 72.0, "actual": True},
                {"key": "solution_change_24h", "label": "第一次换液时间/h", "type": "number", "default": 24.0, "actual": True},
                {"key": "solution_change_48h", "label": "第二次换液时间/h", "type": "number", "default": 48.0, "actual": True},
                {"key": "observation_illuminance", "label": "观察照度/lx", "type": "number", "default": 1000.0, "actual": True},
                {"key": "observation_distance", "label": "观察距离/mm", "type": "number", "default": 250.0, "actual": True},
            ]},
        ],
        "columns": [
            ("sample_no", "试样编号", "text"), ("specimen_role", "试样用途", "select:浸泡试样|未浸泡对照"),
            ("diameter", "直径/mm", "number"), ("thickness", "厚度/mm", "number"), ("surface_prep", "表面制备", "select:符合|不符合"),
            ("color_change", "颜色变化", "select:无|极轻微|明显"), ("tarnish_product", "晦暗产物", "select:无|有"),
            ("removal_ease", "轻柔刷洗/擦拭去除性", "select:易去除|不易去除|不适用"),
            ("reflectance_change", "反射率变化（仅报告）", "text"), ("conclusion", "单样结论", "calc"), ("note", "备注", "text"),
        ],
    },

    # ── generic — 通用实验记录（新实验默认模板）──
    "generic": {
        "title": "通用实验记录",
        "experiment_code": None,
        "sections": [
            {"title": "环境与设备", "fields": COMMON_ENV_FIELDS + COMMON_DEVICE_FIELDS + [
                {"key": "sample_preparation", "label": "样品制备与状态确认", "type": "textarea"},
                {"key": "test_conditions", "label": "试验条件与参数", "type": "textarea"},
                {"key": "procedure_summary", "label": "操作过程摘要", "type": "textarea"},
                {"key": "acceptance_criteria", "label": "接受准则/判定要求", "type": "textarea"},
            ]},
        ],
        "columns": [
            ("sample_no", "样品编号", "text"),
            ("measurement_item", "测量项目/位置", "text"),
            ("raw_value", "原始测量值", "text"),
            ("unit", "单位", "text"),
            ("calculated_value", "计算结果", "text"),
            ("conclusion", "单样结论", "select:符合|不符合|需复核"),
            ("file_no", "数据/图像文件编号", "text"),
            ("note", "备注", "text"),
        ],
    },
}

# ── 自动装配母版补充观察字段 ──
for _kind, _definition in SCHEMAS.items():
    if _kind == "generic":
        continue
    _existing = {f["key"] for s in _definition["sections"] for f in s["fields"]}
    _excluded_common_fields = {
        "mc_crack": {"sample_production_date", "method_execution_confirmation"},
        "thickness": {"sample_preparation_actual", "method_execution_confirmation"},
    }.get(_kind, set())
    _fields = [
        dict(field)
        for field in COMMON_PROCESS_OBSERVATIONS + SUPPLEMENTAL_PROCESS_FIELDS.get(_kind, [])
        if field["key"] not in _existing and field["key"] not in _excluded_common_fields
    ]
    if _fields:
        _definition["sections"].append({"title": "母版补充现场观察", "fields": _fields})
