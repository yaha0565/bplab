# -*- coding: utf-8 -*-
"""Controlled business-to-template mappings.

This module intentionally contains no workflow, numbering, permission or database logic.
It only translates the existing concise experiment payload into existing cells of the
controlled Word mothers.
"""
from __future__ import annotations

from statistics import mean
import re
from typing import Any

from app.services.record_word_engine import BLANK_RE, _compose_cell_text, template_manifest


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _box(original: str, selected: Any) -> str:
    choices = [str(x) for x in selected] if isinstance(selected, (list, tuple, set)) else [str(selected or "")]
    result = str(original or "").replace("☑", "□")
    options = [x.strip() for x in re.split(r"[□☐☑]", result)[1:] if x.strip()]
    for option in options:
        clean = re.sub(r"[_＿…]+.*$", "", option).strip(" ：:；;，,")
        def matches(choice: str) -> bool:
            choice = choice.strip()
            if choice == clean:
                return True
            for word in ("符合", "合格", "正常", "有效", "通过"):
                if word in choice and word in clean and (("不" + word) in choice) != (("不" + word) in clean):
                    return False
            return len(choice) > 1 and len(clean) > 1 and (choice in clean or clean in choice)
        if any(choice and matches(choice) for choice in choices):
            result = re.sub(r"□\s*" + re.escape(clean), lambda m: "☑" + m.group(0)[1:], result, count=1)
    return result


def _positive_box(original: str) -> str:
    positive = [
        "符合", "正常", "合格", "是", "无", "完好", "已确认", "已完成", "通过",
        "清晰", "有效", "牢固", "允许检测", "允许曝光", "不适用", "无修改",
    ]
    result = _box(original, positive)
    if "☑" not in result and ("□" in result or "☐" in result):
        result = result.replace("☐", "□").replace("□", "☑", 1)
    return result


class Writer:
    def __init__(self, template_name: str, values: dict[str, str]):
        self.fields = {field["key"]: field for field in template_manifest(template_name)}
        self.values = values

    def put(self, table: int, row: int, col: int, value: Any, checkbox: bool = False) -> None:
        key = f"t{table}_r{row}_c{col}"
        field = self.fields.get(key)
        if not field:
            return
        original = str(field.get("template_text", "") or "")
        raw = _text(value)
        self.values[key] = _box(original, value) if checkbox else _compose_cell_text(original, raw)

    def put_unused_row(self, table: int, row: int) -> None:
        for key, field in self.fields.items():
            if field["table"] == table and field["row"] == row:
                self.values[key] = "/"

    def finish_defaults(self) -> None:
        """Complete non-business layout markers without creating operator inputs."""
        for key, field in self.fields.items():
            original = str(field.get("template_text", "") or "")
            value = str(self.values.get(key, "") or "")
            if "□" in original or "☐" in original:
                # Rows explicitly marked unused must stay unused. Replacing "/"
                # with the original unchecked choices made empty sample rows look
                # as if the experimenter had forgotten to complete them.
                if value.strip() in {"/", "不适用"}:
                    continue
                # Never manufacture a positive observation. A checkbox is
                # selected only when an explicit UI value or calculation was
                # written through Writer.put(..., checkbox=True).
                if "☑" not in value:
                    self.values[key] = BLANK_RE.sub("/", original.replace("☐", "□").replace("☑", "□"))
                else:
                    # A selected normal option does not require the blank text
                    # attached to an unselected "异常/其他" alternative.
                    self.values[key] = BLANK_RE.sub("/", value)
                continue
            if not value:
                self.values[key] = _compose_cell_text(original, "/")
                # _compose_cell_text 只替换一处 ____，多占位符的单元格需要全部替换
                if BLANK_RE.search(str(self.values.get(key, "") or "")):
                    self.values[key] = BLANK_RE.sub("/", str(self.values[key] or ""))
            elif BLANK_RE.search(value):
                self.values[key] = BLANK_RE.sub("/", value)


def _environment(writer: Writer, table: int, params: dict[str, Any], before_col: int, after_col: int, result_col: int | None = None) -> None:
    writer.put(table, 1, before_col, params.get("temperature_before"))
    writer.put(table, 1, after_col, params.get("temperature_after"))
    writer.put(table, 2, before_col, params.get("humidity_before"))
    writer.put(table, 2, after_col, params.get("humidity_after"))
    if result_col is not None:
        writer.put(table, 1, result_col, "是", True)
        writer.put(table, 2, result_col, "是", True)


def _rough(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    _environment(writer, 2, params, 2, 3, 4)
    writer.put(2, 3, 2, params.get("environment_interference", "无明显干扰"), True)
    writer.put(2, 3, 3, params.get("environment_interference", "无明显干扰"), True)
    writer.put(2, 3, 4, "是", True)
    writer.put(2, 4, 2, "已清洁", True)
    writer.put(2, 4, 4, "是", True)
    writer.put(2, 5, 2, "符合", True)
    writer.put(2, 5, 4, "是", True)
    nominal = params.get("standard_block_nominal")
    measured = params.get("standard_block_measured")
    deviation = None if nominal in (None, "") or measured in (None, "") else round(float(measured) - float(nominal), 4)
    repeats = [params.get(f"repeat_check_{i}") for i in range(1, 4)]
    valid_repeats = [float(x) for x in repeats if x not in (None, "")]
    repeat_mean = round(mean(valid_repeats), 3) if len(valid_repeats) == 3 else ""
    writer.put(4, 3, 2, f"标称值：{_text(nominal)}；实测值：{_text(measured)}；偏差：{_text(deviation)}")
    writer.put(4, 4, 2, f"1：{_text(repeats[0])} 2：{_text(repeats[1])} 3：{_text(repeats[2])} 平均：{_text(repeat_mean)}")
    for row_index in range(1, 7):
        if row_index > len(rows):
            writer.put_unused_row(7, row_index)
            continue
        item = rows[row_index - 1]
        mapping = {
            0: item.get("sample_no"), 2: item.get("ra1"), 3: item.get("ra2"),
            4: item.get("ra3"), 5: item.get("mean"), 7: attachment_ref,
            8: item.get("retest_mean") or "/", 10: context.get("operator"), 11: item.get("note") or "/",
        }
        for col, value in mapping.items():
            writer.put(7, row_index, col, value)
        writer.put(7, row_index, 1, item.get("surface_confirm", "符合"), True)
        writer.put(7, row_index, 6, item.get("position") or "平行纹理", True)
        writer.put(7, row_index, 9, item.get("conclusion"), True)
    means = [float(x["mean"]) for x in rows if x.get("mean") not in (None, "")]
    writer.put(8, 1, 1, f"最小值：{_text(min(means) if means else '')} μm；最大值：{_text(max(means) if means else '')} μm")
    failed = [x.get("sample_no", "") for x in rows if x.get("conclusion") not in ("符合", "合格")]
    writer.put(8, 2, 1, ("无" if not failed else "有"), True)
    writer.put(8, 4, 1, "合格" if not failed else "不合格", True)
    writer.put(8, 5, 1, "全部试样平均Ra均≤15 μm。" if not failed else f"不符合试样：{'、'.join(failed)}。")


def _crack(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    _environment(writer, 1, params, 2, 3, 4)
    writer.put(3, 1, 2, f"金瓷结合试验夹具编号：{params.get('fixture_no','') or 'BPGL-B009'}")
    writer.put(3, 2, 2, f"实测跨距：{_text(params.get('support_span'))}mm（要求20mm）")
    writer.put(3, 3, 2, f"R = {_text(params.get('roller_radius'))} mm（要求1.0 mm）")
    writer.put(3, 6, 2, f"编号：{params.get('parallel_block_no') or 'BGGL-B019'}；规格：（30×6×5） mm")
    writer.put(3, 7, 2, f"平行块平行度：{_text(params.get('parallel_block_parallelism'))} mm")
    writer.put(3, 9, 2, f"夹具平行与居中：{params.get('parallel_check','符合')}")
    writer.put(4, 1, 1, f"试样名称：{params.get('metal_name') or context.get('sample_name','')}；批号：{params.get('metal_batch') or context.get('product_no','')}")
    writer.put(4, 2, 1, f"EM = {_text(rows[0].get('em') if rows else '')} GPa；来源：{params.get('em_source','')}；文件编号：{params.get('em_source_file','')}")
    writer.put(4, 3, 1, "各试样K值及计算结果见原始数据表", True)
    for row_index in range(1, 7):
        if row_index > len(rows):
            writer.put_unused_row(6, row_index)
            continue
        item = rows[row_index - 1]
        keys = ["sample_no", "width", "dm1", "dm2", "dm3", "dm_mean", "em", "k", "ffail", "tau", "crack_position", "failure_mode"]
        for col, key in enumerate(keys):
            writer.put(6, row_index, col, item.get(key))
        writer.put(6, row_index, 12, attachment_ref)
        writer.put(6, row_index, 13, item.get("conclusion"), True)
    writer.put(7, 1, 1, str(sum(x.get("conclusion") == "符合" for x in rows)))
    writer.put(7, 2, 1, "是" if any(x.get("conclusion") != "符合" for x in rows) else "否", True)
    writer.put(7, 4, 1, attachment_ref)
    writer.put(7, 5, 1, "符合要求" if all(x.get("conclusion") == "符合" for x in rows) else "不符合要求", True)


def _xray(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    writer.put(2, 1, 1, params.get("start_time"))
    writer.put(2, 1, 3, params.get("end_time"))
    writer.put(2, 1, 5, context.get("operator"))
    writer.put(2, 2, 1, params.get("temperature_before"))
    writer.put(2, 2, 4, "符合", True)
    writer.put(2, 3, 1, params.get("humidity_before"))
    writer.put(2, 3, 4, "符合", True)
    density_values = [params.get(f"density_measured_{i}") for i in range(1, 4)]
    for col, value in enumerate([params.get("density_nominal")] + density_values, 1):
        writer.put(4, 1, col, value)
    valid_density = [float(x) for x in density_values if x not in (None, "")]
    writer.put(4, 1, 5, round(mean(valid_density), 4) if len(valid_density) == 3 else "")
    writer.put(4, 1, 7, "合格", True)
    first_sample = rows[0] if rows else {}
    writer.put(7, 0, 2, first_sample.get("sample_no"))
    writer.put(7, 0, 6, first_sample.get("image_no") or attachment_ref)
    writer.put(7, 0, 10, params.get("test_date"))
    writer.put(7, 1, 2, params.get("software") or "图像测量软件")
    writer.put(7, 1, 6, context.get("operator"))
    writer.put(7, 1, 10, context.get("reviewer"))
    for roi in range(1, 4):
        table_row = 4 + roi
        values = [first_sample.get(f"roi{roi}_reading{reading}") for reading in range(1, 4)]
        for col, value in zip((3, 5, 7), values):
            writer.put(7, table_row, col, value)
        valid = [float(value) for value in values if value not in (None, "")]
        writer.put(7, table_row, 9, round(mean(valid), 2) if len(valid) == 3 else first_sample.get(f"roi{roi}"))
        writer.put(7, table_row, 11, first_sample.get("note") or "/")
    for point in range(1, 11):
        table_row = 7 + point
        values = [params.get(f"iqi_gray_{point:02d}_{reading}") for reading in range(1, 4)]
        for col, value in zip((3, 5, 7), values):
            writer.put(7, table_row, col, value)
        valid = [float(value) for value in values if value not in (None, "")]
        writer.put(7, table_row, 9, round(mean(valid), 2) if len(valid) == 3 else "")
        writer.put(7, table_row, 11, "/")
    for row_index in range(1, 11):
        if row_index > len(rows):
            writer.put_unused_row(6, row_index)
            continue
        item = rows[row_index - 1]
        writer.put(6, row_index, 0, item.get("sample_no"))
        writer.put(6, row_index, 1, item.get("sample_name_tooth"))
        writer.put(6, row_index, 2, item.get("sample_status", "完好"), True)
        writer.put(6, row_index, 3, attachment_ref)
        writer.put(6, row_index, 4, "咬合面朝下", True)
        writer.put(6, row_index, 5, item.get("iqi_display"), True)
        writer.put(6, row_index, 6, item.get("image_valid"), True)
        writer.put(6, row_index, 7, item.get("retake", "否"), True)
    for row_index in range(1, 7):
        if row_index > len(rows):
            writer.put_unused_row(8, row_index)
            continue
        item = rows[row_index - 1]
        writer.put(8, row_index, 0, item.get("sample_no"))
        writer.put(8, row_index, 1, attachment_ref)
        writer.put(8, row_index, 2, f"ROI-1：{_text(item.get('roi1'))}； ROI-2：{_text(item.get('roi2'))}； ROI-3：{_text(item.get('roi3'))}")
        writer.put(8, row_index, 3, item.get("thickness_relation"))
        writer.put(8, row_index, 4, item.get("estimated_thickness"))
        writer.put(8, row_index, 5, "否" if item.get("conclusion") not in ("超出适用范围",) else "是", True)
        writer.put(8, row_index, 6, item.get("note") or item.get("defect") or "/")


def _warpage(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    for row_index in range(1, 11):
        if row_index > len(rows):
            for table in (4, 6, 8, 9):
                writer.put_unused_row(table, row_index)
            continue
        item = rows[row_index - 1]
        writer.put(4, row_index, 0, item.get("sample_no"))
        writer.put(4, row_index, 1, attachment_ref)
        writer.put(4, row_index, 2, "是", True)
        writer.put(4, row_index, 3, "是", True)
        writer.put(4, row_index, 4, item.get("h1"))
        writer.put(4, row_index, 5, context.get("operator"))
        writer.put(6, row_index, 0, item.get("sample_no"))
        writer.put(6, row_index, 1, f"{item.get('cut_start','')} / {item.get('cut_end','')}")
        writer.put(6, row_index, 2, item.get("coolant_status", "是"), True)
        writer.put(6, row_index, 3, "合格" if item.get("edge_condition") in ("", None, "无") else "不合格", True)
        writer.put(6, row_index, 4, item.get("remade", "否"), True)
        writer.put(8, row_index, 0, item.get("sample_no"))
        writer.put(8, row_index, 1, attachment_ref)
        writer.put(8, row_index, 2, "是", True)
        writer.put(8, row_index, 3, "是", True)
        writer.put(8, row_index, 4, item.get("h2"))
        writer.put(8, row_index, 5, context.get("operator"))
        for col, key in enumerate(("sample_no", "h1", "h2", "delta", "limit")):
            writer.put(9, row_index, col, item.get(key))
        writer.put(9, row_index, 5, item.get("conclusion"), True)
        writer.put(9, row_index, 6, item.get("note") or "/")


def _cte(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    writer.put(1, 1, 2, params.get("temperature_before"))
    writer.put(1, 2, 2, params.get("humidity_before"))
    for row_index in range(1, 7):
        if row_index > len(rows):
            for table in (4, 5, 6):
                writer.put_unused_row(table, row_index)
            continue
        item = rows[row_index - 1]
        writer.put(4, row_index, 0, item.get("sample_no"))
        writer.put(4, row_index, 1, context.get("material"))
        writer.put(4, row_index, 2, item.get("l0"))
        writer.put(4, row_index, 3, item.get("diameter"))
        writer.put(4, row_index, 4, item.get("nominal_value"))
        writer.put(4, row_index, 5, item.get("installation_direction", "正确"), True)
        writer.put(4, row_index, 6, params.get("initial_pv"))
        writer.put(4, row_index, 7, item.get("sample_secure", "是"), True)
        writer.put(4, row_index, 8, item.get("note") or "/")
        writer.put(5, row_index, 0, item.get("sample_no"))
        writer.put(5, row_index, 1, item.get("t1"))
        writer.put(5, row_index, 2, item.get("t2"))
        writer.put(5, row_index, 3, item.get("delta_t"))
        writer.put(5, row_index, 4, item.get("delta_l"))
        writer.put(5, row_index, 5, item.get("run_status", "正常"), True)
        writer.put(5, row_index, 6, item.get("auto_stop", "是"), True)
        writer.put(5, row_index, 7, attachment_ref)
        writer.put(5, row_index, 8, item.get("validity", "有效"), True)
        result_values = (
            item.get("sample_no"),
            f"{_text(item.get('t1'))}～{_text(item.get('t2'))}",
            item.get("l0"),
            item.get("delta_t"),
            item.get("delta_l"),
            item.get("alpha"),
            (
                f"样品标准值：{_text(item.get('sample_standard_value'))}；"
                f"判定依据：{item.get('judgement_basis','')}；"
                f"判定标准：{item.get('judgement_standard','')}"
            ).strip("；"),
        )
        for col, value in enumerate(result_values):
            writer.put(6, row_index, col, value)
        writer.put(6, row_index, 7, item.get("judgement_result") or "符合", True)
        writer.put(6, row_index, 8, item.get("note") or "/")
    alphas = [float(x["alpha"]) for x in rows if x.get("alpha") not in (None, "")]
    writer.put(8, 1, 0, "合格" if all(x.get("judgement_result") in ("符合", "合格", "", None) for x in rows) else "不合格", True)
    writer.put(8, 2, 1, round(mean(alphas), 3) if alphas else "")
    writer.put(8, 3, 1, max([float(x.get("delta_l")) for x in rows if x.get("delta_l") not in (None, "")], default=""))
    writer.put(8, 2, 3, f"{params.get('start_temperature','')} ℃ ～ {params.get('end_temperature','')} ℃")
    writer.put(8, 3, 3, attachment_ref)


def _shock(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    _environment(writer, 1, params, 2, 3, 4)
    writer.put(1, 3, 2, params.get("illumination"))
    writer.put(1, 3, 3, params.get("illumination"))
    writer.put(1, 3, 4, "是", True)
    writer.put(4, 1, 2, "无异常", True)
    writer.put(4, 2, 2, f"设定：{_text(params.get('oven_temperature'))}℃；稳定读数：{_text(params.get('oven_temperature'))}℃")
    writer.put(4, 3, 2, f"开始：{params.get('first_heating_start','')}；结束：{params.get('first_heating_end','')}；时长：{_text(params.get('first_heating_time'))}min")
    writer.put(4, 4, 2, "碎冰比例：1/2～2/3；静置：2min")
    writer.put(4, 5, 2, f"稳定读数：{_text(params.get('ice_water_temperature'))}℃；读数时间：{params.get('monitor_1_time','')}")
    writer.put(4, 6, 2, f"实际：{_text(params.get('transfer_time'))}s")
    writer.put(4, 7, 2, f"开始：{params.get('ice_immersion_start','')}；结束：{params.get('ice_immersion_end','')}；时长：{_text(params.get('immersion_time'))}min")
    writer.put(4, 8, 2, f"温度：{_text(params.get('oven_temperature'))}℃；时长：{_text(params.get('second_heating_time'))}min")
    for row_index in range(1, 6):
        writer.put(5, row_index, 2, params.get(f"monitor_{row_index}_time"))
        writer.put(5, row_index, 3, params.get(f"monitor_{row_index}_temperature"))
        writer.put(5, row_index, 4, params.get(f"monitor_{row_index}_stable", "是"), True)
        status = params.get(f"monitor_{row_index}_status", "符合")
        note = params.get(f"monitor_{row_index}_note") or ""
        writer.put(5, row_index, 5, f"{status}" + (f"；{note}" if note else ""), True)
        writer.put(5, row_index, 6, context.get("operator"))
    writer.put(6, 1, 0, params.get("container_no") or "/")
    writer.put(6, 1, 1, len(rows))
    writer.put(6, 1, 2, f"{params.get('first_heating_start','')}-{params.get('first_heating_end','')}")
    writer.put(6, 1, 3, f"{params.get('ice_immersion_start','')} / {_text(params.get('transfer_time'))}s")
    writer.put(6, 1, 4, f"{params.get('ice_immersion_start','')}-{params.get('ice_immersion_end','')}")
    writer.put(6, 1, 5, f"{params.get('second_heating_start','')}-{params.get('second_heating_end','')}")
    writer.put(7, 1, 2, f"环境温度：{_text(params.get('cooling_temperature'))}℃；☑无直吹风 ☑无阳光直射")
    writer.put(7, 2, 2, f"读数：{_text(params.get('surface_temperature'))}℃；稳定时间：30s")
    writer.put(7, 3, 2, f"冷却开始：{params.get('cooling_start','')}；完成：{params.get('cooling_end','')}")
    writer.put(7, 4, 2, f"照度：{_text(params.get('illumination'))}lx；放大镜：☑{_text(params.get('magnification'))}×")
    writer.put(7, 5, 2, f"检查人员：{context.get('operator','')}")
    for row_index in range(1, 29):
        if row_index > len(rows):
            writer.put_unused_row(8, row_index)
            continue
        item = rows[row_index - 1]
        writer.put(8, row_index, 0, item.get("sample_no"))
        writer.put(8, row_index, 1, item.get("initial_appearance", "无异常"), True)
        writer.put(8, row_index, 2, item.get("crack"), True)
        writer.put(8, row_index, 3, item.get("chipping"), True)
        writer.put(8, row_index, 4, item.get("fracture"), True)
        writer.put(8, row_index, 5, item.get("conclusion"), True)
        writer.put(8, row_index, 6, item.get("note") or attachment_ref)
    writer.put(9, 1, 1, len(rows))
    writer.put(9, 1, 3, len(rows))
    writer.put(9, 2, 1, sum(x.get("crack") == "有" for x in rows))
    writer.put(9, 2, 3, sum(x.get("chipping") == "有" for x in rows))
    writer.put(9, 3, 1, sum(x.get("fracture") == "有" for x in rows))
    failed = [x for x in rows if x.get("conclusion") != "符合"]
    writer.put(9, 4, 3, "合格" if not failed else "不合格", True)
    writer.put(9, 5, 1, "经耐急冷急热试验后，样品未见裂纹、崩瓷、破裂，判定合格。" if not failed else "试验后存在裂纹、崩瓷或破裂，判定不合格。", True)


def _bending(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    for row_index in range(1, 7):
        if row_index > len(rows):
            writer.put_unused_row(4, row_index)
            continue
        item = rows[row_index - 1]
        mapping = ("sample_no", "length", "width", "height", "span", "speed", "fmax", "stress_02")
        for col, key in enumerate(mapping):
            writer.put(4, row_index, col, item.get(key))
        writer.put(4, row_index, 8, item.get("sample_state"), True)
        writer.put(4, row_index, 9, item.get("conclusion"), True)
        writer.put(4, row_index, 10, item.get("note") or "/")
    overall = "全部符合" if all(x.get("conclusion") == "符合" for x in rows) else "存在不符合"
    writer.put(4, 7, 0, overall, True)
    writer.put(7, 1, 0, attachment_ref)
    writer.put(7, 2, 2, "有" if attachment_ref else "无", True)
    writer.put(7, 2, 4, "有" if attachment_ref else "无", True)


def _vickers(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    writer.put(2, 1, 5, params.get("standard_block_due"))
    writer.put(2, 2, 3, params.get("standard_block_reading_1"))
    writer.put(2, 2, 5, params.get("standard_block_reading_2"))
    writer.put(2, 3, 1, params.get("standard_block_reading_3"))
    values = [params.get(f"standard_block_reading_{i}") for i in range(1, 4)]
    valid = [float(x) for x in values if x not in (None, "")]
    writer.put(2, 3, 3, round(mean(valid), 1) if len(valid) == 3 else "")
    writer.put(2, 3, 5, params.get("standard_block_result"), True)
    writer.put(2, 4, 5, "符合" if params.get("surface_condition") == "平整清洁" else "不符合", True)
    writer.put(2, 5, 1, params.get("surface_condition"), True)
    writer.put(2, 5, 5, params.get("perpendicularity"), True)
    writer.put(3, 1, 1, params.get("indent_measurement_method", "切线测量"), True)
    writer.put(3, 2, 3, "已导出" if params.get("report_exported") == "是" else "未导出", True)
    writer.put(3, 2, 5, "是", True)
    for row_index in range(1, 13):
        if row_index > len(rows):
            writer.put_unused_row(5, row_index)
            continue
        item = rows[row_index - 1]
        mapping = ("sample_no", "face", "indent1", "indent2", "indent3", "mean")
        for col, key in enumerate(mapping):
            writer.put(5, row_index, col, item.get(key))
        writer.put(5, row_index, 6, item.get("indent_quality", "有效"), True)
        writer.put(5, row_index, 7, params.get("test_force"))
        writer.put(5, row_index, 8, params.get("dwell_time"))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        grouped.setdefault(str(item.get("sample_no", "")), []).append(item)
    for row_index, (sample_no, items) in enumerate(grouped.items(), 1):
        if row_index > 6:
            break
        writer.put(6, row_index, 0, sample_no)
        writer.put(6, row_index, 1, items[0].get("mean") if items else "")
        writer.put(6, row_index, 2, items[1].get("mean") if len(items) > 1 else "")
        writer.put(6, row_index, 3, items[0].get("limit") or "按委托/技术要求")
        writer.put(6, row_index, 4, "不判定", True)
        writer.put(6, row_index, 5, attachment_ref)


def _thickness(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    writer.put(0, 7, 1, f"样品批号：{params.get('sample_production_date') or context.get('product_no','')}")
    writer.put(0, 7, 3, f"生产日期：{params.get('production_date') or context.get('production_date','')}")
    writer.put(0, 7, 5, f"设计文件编号：{params.get('design_file_no','')}")
    writer.put(2, 1, 2, f"测试放大倍数：{params.get('magnification') or '33倍'}")
    writer.put(2, 2, 2, f"开始：{params.get('preheat_start','')} 结束：{params.get('preheat_end','')}")
    nominal, measured = params.get("calibration_nominal"), params.get("calibration_measured")
    error = None if nominal in (None, "") or measured in (None, "") else round(float(measured) - float(nominal), 4)
    writer.put(2, 3, 2, f"标准量块标称值：{_text(nominal)} mm 实测值：{_text(measured)} mm 误差：{_text(error)} mm")
    data_rows = list(range(3, 18, 3))
    for sample_index, start_row in enumerate(data_rows):
        if sample_index >= len(rows):
            for row_index in range(start_row, min(start_row + 3, 18)):
                writer.put_unused_row(4, row_index)
            continue
        item = rows[sample_index]
        for repeat_offset in range(3):
            row_index = start_row + repeat_offset
            writer.put(4, row_index, 0, item.get("sample_no"))
            writer.put(4, row_index, 1, repeat_offset + 1)
            values = [item.get(f"r{repeat_offset + 1}_{section}") for section in ("fixed", "middle", "free")]
            for col, value in enumerate(values, 2):
                writer.put(4, row_index, col, value)
            writer.put(4, row_index, 5, item.get(f"r{repeat_offset + 1}_mean"))
            writer.put(4, row_index, 6, item.get("image_no") or attachment_ref)
            writer.put(4, row_index, 7, item.get("data_file_no") or attachment_ref)
            writer.put(4, row_index, 8, item.get("note") or "/")
    for row_index in range(1, 6):
        if row_index > len(rows):
            writer.put_unused_row(5, row_index)
            continue
        item = rows[row_index - 1]
        values = [
            item.get("sample_no"), params.get("design_thickness"), item.get("fixed_mean"),
            item.get("middle_mean"), item.get("free_mean"), item.get("mean"),
            item.get("deviation"), "±0.05 mm",
        ]
        for col, value in enumerate(values):
            writer.put(5, row_index, col, value)
        writer.put(5, row_index, 8, item.get("conclusion"), True)
        writer.put(5, row_index, 9, item.get("note") or "/")


def _color(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    writer.put(1, 1, 1, params.get("temperature_before"))
    writer.put(1, 1, 3, params.get("humidity_before"))
    writer.put(1, 2, 1, "D65灯箱", True)
    writer.put(1, 2, 5, "清洁", True)
    writer.put(1, 3, 5, "已确认", True)
    observer_names = [params.get(f"observer_{index}") or f"观察者{index}" for index in range(1, 4)]
    for table_row, observer in enumerate(observer_names, 5):
        writer.put(1, table_row, 1, observer)
        writer.put(1, table_row, 2, params.get("observer_qualification"))
        writer.put(1, table_row, 4, "否", True)
        writer.put(1, table_row, 5, "合格", True)
        writer.put(1, table_row, 6, observer)
    writer.put(4, 0, 1, params.get("lamp_no"))
    writer.put(4, 0, 3, params.get("lamp_hours"))
    writer.put(4, 1, 1, params.get("filter_no"))
    writer.put(4, 1, 3, params.get("filter_hours"))
    writer.put(4, 2, 3, "是", True)
    writer.put(4, 3, 3, "历史记录", True)
    writer.put(5, 1, 2, params.get("source_type"), True)
    writer.put(5, 2, 2, f"设定：{_text(params.get('water_temperature'))}℃；实测：{_text(params.get('color_monitor_1_water_temperature'))}℃")
    writer.put(5, 3, 2, params.get("sample_illuminance"))
    writer.put(5, 4, 2, params.get("water_distance"))
    writer.put(5, 5, 2, f"设定：{_text(params.get('exposure_time'))} h")
    writer.put(5, 6, 2, "平行；无阴影", True)
    writer.put(5, 7, 2, "正常", True)
    for table_row in range(1, 8):
        writer.put(5, table_row, 3, "是", True)
        writer.put(5, table_row, 4, context.get("operator"))
    writer.put(7, 0, 1, params.get("exposure_start"))
    writer.put(7, 0, 3, params.get("exposure_end"))
    writer.put(7, 1, 1, params.get("exposure_time"))
    writer.put(7, 1, 3, "是", True)
    writer.put(7, 2, 1, attachment_ref)
    writer.put(7, 2, 3, "详见内部实验数据追溯Excel")
    writer.put(7, 3, 1, "有" if attachment_ref else "无", True)
    writer.put(7, 3, 3, "有" if attachment_ref else "无", True)
    for table_row in range(1, 7):
        writer.put(8, table_row, 1, params.get(f"color_monitor_{table_row}_datetime"))
        writer.put(8, table_row, 2, params.get(f"color_monitor_{table_row}_runtime"))
        writer.put(8, table_row, 3, params.get(f"color_monitor_{table_row}_water_temperature"))
        writer.put(8, table_row, 4, params.get(f"color_monitor_{table_row}_illuminance"))
        writer.put(8, table_row, 5, params.get(f"color_monitor_{table_row}_distance"))
        writer.put(8, table_row, 6, params.get(f"color_monitor_{table_row}_device_status", "正常"), True)
        writer.put(8, table_row, 7, params.get(f"color_monitor_{table_row}_sample_status", "正常"), True)
        writer.put(8, table_row, 8, context.get("operator"))
        writer.put(8, table_row, 9, params.get(f"color_monitor_{table_row}_note") or "/")
    writer.put(9, 0, 1, ["去除遮盖", "吸除表面水分", "未擦伤/污染试样"], True)
    writer.put(9, 0, 3, "正常", True)
    writer.put(9, 1, 1, params.get("lamp_box_ready"), True)
    writer.put(9, 1, 3, params.get("d65_illuminance"))
    writer.put(9, 2, 1, params.get("background"), True)
    writer.put(9, 2, 3, "合格", True)
    writer.put(9, 3, 1, params.get("observation_distance"))
    writer.put(9, 3, 3, params.get("single_observation_time"))
    writer.put(9, 4, 1, ["无明显颜色反射", "光源无闪烁", "区域清洁"], True)
    writer.put(9, 4, 3, params.get("observation_date"))
    for row_index in range(1, 13):
        if row_index > len(rows):
            writer.put_unused_row(6, row_index)
            continue
        item = rows[row_index - 1]
        writer.put(6, row_index, 0, item.get("sample_no"))
        writer.put(6, row_index, 1, item.get("control_no") or "/")
        writer.put(6, row_index, 2, item.get("shape"), True)
        writer.put(6, row_index, 4, item.get("cover_method"), True)
        writer.put(6, row_index, 5, item.get("cover_direction"))
        writer.put(6, row_index, 6, item.get("cover_secure"), True)
        writer.put(6, row_index, 8, "是" if attachment_ref else "否", True)
        writer.put(6, row_index, 9, item.get("note") or "/")
        for observer_index, observer_name in enumerate(observer_names, 1):
            detail_row = (row_index - 1) * 3 + observer_index
            if detail_row >= 19:
                break
            result = item.get(f"observer{observer_index}")
            writer.put(10, detail_row, 0, item.get("sample_no"))
            writer.put(10, detail_row, 1, observer_name)
            writer.put(10, detail_row, 2, "合格", True)
            writer.put(10, detail_row, 3, result)
            writer.put(10, detail_row, 4, result)
            writer.put(10, detail_row, 5, result, True)
            writer.put(10, detail_row, 6, observer_name)
            writer.put(10, detail_row, 7, params.get("observation_date"))
    for row_index in range(1, 13):
        if row_index > len(rows):
            writer.put_unused_row(11, row_index)
            continue
        item = rows[row_index - 1]
        writer.put(11, row_index, 0, item.get("sample_no"))
        writer.put(11, row_index, 1, item.get("observer1"), True)
        writer.put(11, row_index, 2, item.get("observer2"), True)
        writer.put(11, row_index, 3, item.get("observer3"), True)
        writer.put(11, row_index, 4, item.get("overall"), True)
        writer.put(11, row_index, 5, "是", True)
        writer.put(11, row_index, 6, item.get("conclusion"), True)
        writer.put(11, row_index, 7, item.get("note") or "/")
    overall = "未见明显色泽差异" if all(x.get("conclusion") == "符合" for x in rows) else "可见明显色泽差异"
    writer.put(11, 13, 1, overall, True)
    writer.put(11, 13, 5, "合格" if all(x.get("conclusion") == "符合" for x in rows) else "不合格", True)


def _fixed_denture(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    for index in range(1, 7):
        if index > len(rows):
            writer.put_unused_row(4, index)
            writer.put_unused_row(6, index)
            continue
        item = rows[index - 1]
        writer.put(4, index, 0, item.get("sample_no"))
        for col in range(1, 5):
            writer.put(4, index, col, item.get("common_check"), True)
        for col, key in ((5, "junction_thickness"), (6, "base_thickness"), (7, "connector_area")):
            writer.put(4, index, col, item.get(key))
        writer.put(4, index, 8, item.get("conclusion"), True)
        writer.put(4, index, 9, item.get("note") or "/")
        writer.put(6, index, 0, item.get("sample_no"))
        for col in range(1, 8):
            writer.put(6, index, col, item.get("finished_check"), True)
        writer.put(6, index, 8, item.get("conclusion"), True)
        writer.put(6, index, 9, item.get("note") or "/")
    for index in range(1, 5):
        if index > len(rows):
            for table in (5, 7, 8):
                writer.put_unused_row(table, index)
            continue
        item = rows[index - 1]
        writer.put(5, index, 0, item.get("sample_no"))
        writer.put(5, index, 1, params.get("material_category"), True)
        writer.put(5, index, 3, item.get("connector_n"))
        writer.put(5, index, 4, item.get("connector_m"))
        writer.put(5, index, 6, item.get("connector_area"))
        writer.put(5, index, 7, f"≥{_text(item.get('connector_limit'))} mm²")
        writer.put(5, index, 8, item.get("conclusion") if params.get("connector_applicable") == "适用" else "不适用", True)
        writer.put(7, index, 0, item.get("sample_no"))
        writer.put(7, index, 1, "是" if params.get("roughness_applicable") == "适用" else "否", True)
        writer.put(7, index, 2, "BPGL-B002")
        writer.put(7, index, 6, "Ra≤0.025 μm")
        rough_ok = item.get("roughness") not in (None, "") and float(item.get("roughness")) <= 0.025
        writer.put(7, index, 7, ("符合" if rough_ok else "不符合") if params.get("roughness_applicable") == "适用" else "不适用", True)
        writer.put(7, index, 8, item.get("note") or "/")
        writer.put(8, index, 0, item.get("sample_no"))
        writer.put(8, index, 2, attachment_ref)
        writer.put(8, index, 3, item.get("pores_over30"))
        writer.put(8, index, 4, item.get("pores_40_150"))
        writer.put(8, index, 5, item.get("pore_over150"), True)
        writer.put(8, index, 7, item.get("conclusion") if params.get("porosity_applicable") == "适用" else "不适用", True)
    overall = "合格" if rows and all(row.get("conclusion") == "符合" for row in rows) else "不合格"
    writer.put(10, 1, 1, "是", True)
    writer.put(10, 4, 1, "否", True)
    writer.put(10, 5, 1, overall, True)
    writer.put(10, 6, 1, attachment_ref)


def _removable_denture(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    item = rows[0] if rows else {}
    for row_index in range(1, 11):
        writer.put(6, row_index, 3, item.get("common_check"), True)
        writer.put(6, row_index, 4, item.get("common_check"), True)
    selected_rows = (1, 2) if params.get("denture_type") == "全口义齿" else (3, 4)
    for row_index in range(1, 5):
        if row_index not in selected_rows or not rows:
            writer.put(7, row_index, 7, "不适用", True)
            continue
        edge = row_index in (1, 3)
        keys = ("edge1", "edge2", "edge3", "edge_mean") if edge else ("middle1", "middle2", "middle3", "middle_mean")
        for col, key in enumerate(keys, 3):
            writer.put(7, row_index, col, item.get(key))
        writer.put(7, row_index, 7, item.get("thickness_conclusion"), True)
    writer.put(9, 2, 1, attachment_ref)
    writer.put(9, 3, 1, params.get("iqi_no"))
    writer.put(9, 6, 1, attachment_ref)
    writer.put(9, 10, 1, item.get("xray_conclusion") if params.get("xray_applicable") == "适用" else "不适用", True)
    writer.put(10, 1, 2, params.get("cutting_device_no"))
    writer.put(10, 2, 3, item.get("outer_angle"))
    writer.put(10, 2, 4, item.get("termination_conclusion") if params.get("termination_applicable") == "适用" else "不适用", True)
    writer.put(10, 3, 3, item.get("inner_angle"))
    writer.put(10, 3, 4, item.get("termination_conclusion") if params.get("termination_applicable") == "适用" else "不适用", True)
    writer.put(10, 4, 3, item.get("same_vertical"), True)
    writer.put(10, 4, 4, item.get("termination_conclusion") if params.get("termination_applicable") == "适用" else "不适用", True)
    writer.put(11, 1, 7, item.get("upper_no_pore_faces"))
    writer.put(11, 1, 8, item.get("porosity_conclusion") if params.get("porosity_applicable") == "适用" else "不适用", True)
    writer.put(11, 2, 7, item.get("lower_no_pore_faces"))
    writer.put(11, 2, 8, item.get("porosity_conclusion") if params.get("porosity_applicable") == "适用" else "不适用", True)
    # SOP-015 is the controlled deletion version: color stability is never
    # performed inside this integrated task; independent color work uses R012.
    for table in (13, 14):
        for row_index in range(1, 8):
            writer.put_unused_row(table, row_index)
    writer.put(15, 1, 1, item.get("conclusion"), True)
    writer.put(15, 4, 1, "否", True)


def _density(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    writer.put(2, 0, 7, params.get("balance_internal_calibration"), True)
    writer.put(3, 6, 7, params.get("system_check_result"), True)
    writer.put(4, 4, 3, params.get("auto_calc_check"), True)
    for sample_index in range(6):
        if sample_index >= len(rows):
            writer.put_unused_row(7, sample_index + 1)
            continue
        item = rows[sample_index]
        for repeat in range(1, 4):
            table_row = sample_index * 3 + repeat
            writer.put(6, table_row, 0, item.get("sample_no"))
            writer.put(6, table_row, 1, repeat)
            for col, key in ((2, f"a{repeat}"), (3, f"b{repeat}"), (4, f"water_temp{repeat}"), (5, f"water_density{repeat}"), (6, f"auto_density{repeat}")):
                writer.put(6, table_row, col, item.get(key))
            valid = item.get(f"density{repeat}") not in (None, "")
            writer.put(6, table_row, 7, "有" if valid else "无", True)
            writer.put(6, table_row, 8, "是" if valid else "否", True)
            writer.put(6, table_row, 9, "符合" if valid else "不符合", True)
            writer.put(6, table_row, 10, item.get("data_file_no") or attachment_ref)
            writer.put(6, table_row, 11, "有效" if valid else "无效", True)
            writer.put(6, table_row, 12, item.get("note") or "/")
        table_row = sample_index + 1
        values = [item.get("sample_no"), item.get("density1"), item.get("density2"), item.get("density3"), item.get("density_difference"), item.get("mean"), round(item.get("mean"), 1) if item.get("mean") is not None else "", params.get("declared_density"), item.get("relative_deviation"), "±5%"]
        for col, value in enumerate(values):
            writer.put(7, table_row, col, value)
        conclusion = "不判定" if item.get("conclusion") == "仅报告结果" else item.get("conclusion")
        writer.put(7, table_row, 10, conclusion, True)
        writer.put(7, table_row, 11, item.get("note") or "/")
    means = [float(row["mean"]) for row in rows if row.get("mean") is not None]
    overall_mean = round(sum(means) / len(means), 4) if len(means) == 6 else ""
    writer.put(7, 7, 1, overall_mean)
    writer.put(7, 7, 3, round(overall_mean, 1) if overall_mean != "" else "")
    writer.put(7, 7, 4, "全部符合" if rows and all(row.get("conclusion") == "符合" for row in rows) else "仅报告结果" if rows and all(row.get("conclusion") == "仅报告结果" for row in rows) else "存在不符合", True)
    writer.put(10, 1, 1, params.get("declared_density_source"))
    writer.put(10, 1, 3, params.get("declared_density"))
    writer.put(10, 3, 1, "符合" if rows and all(row.get("conclusion") == "符合" for row in rows) else "仅报告实测结果不作判定" if rows and all(row.get("conclusion") == "仅报告结果" for row in rows) else "不符合", True)
    writer.put(10, 4, 1, attachment_ref)


def _tarnish(writer: Writer, rows: list[dict[str, Any]], params: dict[str, Any], context: dict[str, Any], attachment_ref: str) -> None:
    for row_index in range(1, 3):
        if row_index > len(rows):
            writer.put_unused_row(3, row_index)
            continue
        item = rows[row_index - 1]
        for col, key in enumerate(("sample_no", "specimen_role", "diameter", "thickness")):
            writer.put(3, row_index, col, item.get(key), key == "specimen_role")
        writer.put(3, row_index, 5, item.get("surface_prep"), True)
        writer.put(3, row_index, 6, "符合" if item.get("conclusion") != "不符合" else "不符合", True)
    for row_index, key in enumerate(("solution_mass_initial", "solution_mass_24h", "solution_mass_48h"), 1):
        writer.put(4, row_index, 2, params.get(key))
        writer.put(4, row_index, 3, "BPGL-A025")
        writer.put(4, row_index, 4, "BPGL-C006")
    writer.put(5, 1, 2, 1000)
    writer.put(5, 2, 2, f"{_text(params.get('bath_temperature'))} ℃")
    writer.put(5, 3, 2, params.get("cycle_immersion_seconds"))
    writer.put(5, 5, 2, params.get("solution_change_24h"))
    writer.put(5, 6, 2, params.get("solution_change_48h"))
    writer.put(5, 7, 2, params.get("total_duration"))
    writer.put(5, 8, 2, "正常", True)
    immersed = next((row for row in rows if row.get("specimen_role") == "浸泡试样"), rows[0] if rows else {})
    control = next((row for row in rows if row.get("specimen_role") == "未浸泡对照"), {})
    writer.put(7, 2, 2, params.get("observation_illuminance"))
    writer.put(7, 3, 2, _text(params.get("observation_distance")))
    writer.put(7, 5, 2, immersed.get("color_change"))
    writer.put(7, 5, 3, control.get("color_change"))
    writer.put(7, 6, 2, immersed.get("reflectance_change"))
    writer.put(7, 7, 2, immersed.get("tarnish_product"), True)
    writer.put(8, 1, 0, immersed.get("sample_no"))
    writer.put(8, 1, 3, immersed.get("removal_ease"), True)
    writer.put(9, 1, 1, immersed.get("color_change"), True)
    writer.put(9, 2, 1, immersed.get("removal_ease"), True)
    writer.put(9, 3, 1, immersed.get("reflectance_change"))
    writer.put(9, 4, 1, "符合抗晦暗要求" if immersed.get("conclusion") == "符合" else "不符合抗晦暗要求", True)
    writer.put(12, 1, 1, "是", True)
    writer.put(12, 2, 1, immersed.get("conclusion"), True)
    writer.put(12, 4, 3, attachment_ref)


MAPPERS = {
    "rough": _rough,
    "mc_crack": _crack,
    "xray": _xray,
    "warp": _warpage,
    "cte": _cte,
    "shock": _shock,
    "bend": _bending,
    "hv": _vickers,
    "thickness": _thickness,
    "color": _color,
    "fixed_denture": _fixed_denture,
    "removable_denture": _removable_denture,
    "density": _density,
    "tarnish": _tarnish,
}


def apply_controlled_mapping(
    template_name: str,
    kind: str,
    values: dict[str, str],
    context: dict[str, Any],
    business_record: dict[str, Any],
    attachment_ref: str,
) -> dict[str, str]:
    writer = Writer(template_name, values)
    params = business_record.get("parameters") or {}
    mapper = MAPPERS.get(kind)
    if mapper:
        mapper(
            writer,
            business_record.get("rows") or [],
            business_record.get("parameters") or {},
            context,
            attachment_ref,
        )
    if kind == "cte":
        # These confirmations already come from the task confirmation,
        # equipment check and pre-check panels. Reflect them into the controlled
        # mother template instead of asking the experimenter to repeat them.
        all_conform = all(
            item.get("judgement_result") in ("符合", "合格", "", None)
            for item in (business_record.get("rows") or [])
        )
        for field in template_manifest(template_name):
            original = str(field.get("template_text") or "")
            combined = " ".join([
                str(field.get("section") or ""),
                str(field.get("label") or ""),
                str(field.get("row_label") or ""),
                str(field.get("col_header") or ""),
            ])
            if "制样/处理状态" in combined:
                writer.values[field["key"]] = _box(
                    original, params.get("sample_processing_state", "原始状态")
                )
            elif any(section in combined for section in (
                "环境条件与试验安全确认",
                "试验前准备与关键参数确认",
            )) and ("□" in original or "☐" in original):
                writer.values[field["key"]] = _box(
                    original, ["是", "无", "正常", "已确认"]
                )
            elif "是否符合委托要求" in combined:
                writer.values[field["key"]] = _box(
                    original, "是" if all_conform else "否"
                )
            elif "复核意见" in combined:
                writer.values[field["key"]] = "/"
    writer.finish_defaults()
    return writer.values
