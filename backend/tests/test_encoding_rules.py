"""编码规则模块 — 单元测试"""
from __future__ import annotations

import pytest

# Import the encoding rules module
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.encoding_rules import (
    generate_commission_no,
    generate_sample_group_no,
    generate_sample_no,
    generate_task_no,
    generate_report_no,
    generate_objection_no,
    generate_hazardous_waste_no,
    validate_commission_no,
    validate_sample_group_no,
    build_sample_name,
    template_code_for_kind,
    COMMISSION_PREFIX,
    SAMPLE_GROUP_PREFIX,
    REPORT_PREFIX,
    OBJECTION_PREFIX,
    HAZARDOUS_WASTE_PREFIX,
    KIND_TO_TEMPLATE,
    MATERIAL_ABBREVIATIONS,
    SAMPLE_TYPE_CODES,
)


class TestCommissionNumbering:
    """委托编号规则"""

    def test_commission_prefix(self):
        """委托编号以 WT 开头"""
        assert COMMISSION_PREFIX == "WT"

    def test_generate_commission_no(self):
        """生成委托编号格式正确"""
        no = generate_commission_no("2026-08-09", 1)
        assert no == "WT20260809001"
        assert len(no) == 13  # WT + 8位日期 + 3位序号

    def test_generate_commission_no_seq_3digits(self):
        """序号为3位格式"""
        no = generate_commission_no("2026-08-09", 5)
        assert no.endswith("005")

    def test_generate_commission_no_large_seq(self):
        """大序号"""
        no = generate_commission_no("2026-08-09", 999)
        assert no.endswith("999")

    def test_validate_valid_commission_no(self):
        """验证合法委托编号"""
        assert validate_commission_no("WT20260809001") is True

    def test_validate_invalid_prefix(self):
        """验证非法前缀"""
        assert validate_commission_no("CX20260809001") is False

    def test_validate_invalid_length(self):
        """验证非法长度"""
        assert validate_commission_no("WT20260809001X") is False


class TestSampleGroupNumbering:
    """样品组编号规则"""

    def test_generate_sample_group_no(self):
        """生成样品组编号"""
        no = generate_sample_group_no("2026-08-09", 1)
        assert no == "BP20260809001"
        assert no.startswith("BP")
        assert len(no) == 13

    def test_validate_sample_group_no(self):
        """验证样品组编号"""
        assert validate_sample_group_no("BP20260809001") is True
        assert validate_sample_group_no("WX20260809001") is False


class TestSampleNumbering:
    """实验样品编号规则"""

    def test_generate_sample_no(self):
        """生成实验样品编号"""
        no = generate_sample_no("BP20260809001", 1)
        assert no == "BP20260809001-S01"

    def test_generate_sample_no_two_digit(self):
        """序号为2位"""
        no = generate_sample_no("BP20260809001", 5)
        assert no.endswith("-S05")


class TestTaskNumbering:
    """实验任务编号规则"""

    def test_generate_task_no(self):
        """生成实验任务编号"""
        no = generate_task_no("BP20260809001", 1)
        assert no == "BP20260809001-T01"

    def test_generate_task_no_two_digit(self):
        """序号为2位"""
        no = generate_task_no("BP20260809001", 12)
        assert no.endswith("-T12")


class TestReportNumbering:
    """报告编号规则"""

    def test_generate_report_no(self):
        """生成报告编号"""
        no = generate_report_no("2026-08-09", 1, 1)
        assert no == "R20260809001-T01"

    def test_generate_report_no_with_task_seq(self):
        """包含任务序号"""
        no = generate_report_no("2026-08-09", 5, 3)
        assert no == "R20260809005-T03"


class TestOtherNumbering:
    """其他编号规则"""

    def test_objection_no(self):
        """异议单编号"""
        no = generate_objection_no("2026-08-09", 1)
        assert no == "Y20260809001"

    def test_hazardous_waste_no(self):
        """危废登记编号"""
        no = generate_hazardous_waste_no("2026-08-09", 1)
        assert no == "D20260809001"


class TestSampleNaming:
    """样品命名规范"""

    def test_build_sample_name_basic(self):
        """基本样品命名"""
        name = build_sample_name("SY", "TH", 1, "1")
        assert name == "SY-TH-01-1"

    def test_build_sample_name_with_int_sequence(self):
        """序号为整数"""
        name = build_sample_name("GD", "GG", 5, "A")
        assert name == "GD-GG-05-A"

    def test_sample_type_codes(self):
        """样品类型代码字典"""
        assert SAMPLE_TYPE_CODES["SY"] == "试样"
        assert SAMPLE_TYPE_CODES["GD"] == "固定"
        assert SAMPLE_TYPE_CODES["HD"] == "活动"

    def test_material_abbreviations(self):
        """材料缩写字典"""
        assert "TH" in MATERIAL_ABBREVIATIONS
        assert "GG" in MATERIAL_ABBREVIATIONS
        assert "CC" in MATERIAL_ABBREVIATIONS


class TestTemplateMapping:
    """记录模板编号映射"""

    def test_known_kind(self):
        """已知实验类型映射"""
        assert template_code_for_kind("rough") == "R001"
        assert template_code_for_kind("hv") == "R011"
        assert template_code_for_kind("color") == "R012"

    def test_unknown_kind(self):
        """未知实验类型"""
        assert template_code_for_kind("unknown_kind") == "R000"

    def test_all_kinds_have_mapping(self):
        """所有 12 种实验类型都有模板映射"""
        for kind in KIND_TO_TEMPLATE:
            assert KIND_TO_TEMPLATE[kind].startswith("R")


class TestEvaluationStandards:
    """评价标准"""

    def test_get_standard(self):
        """获取评价标准"""
        from app.core.evaluation_standards import get_standard, get_requirement_text
        std = get_standard("rough")
        assert std is not None
        assert std["standard"] == "YY/T 1702"

        text = get_requirement_text("rough")
        assert "Ra" in text or "μm" in text

    def test_get_standard_unknown(self):
        """未知实验类型"""
        from app.core.evaluation_standards import get_standard
        assert get_standard("nonexistent") is None

    def test_validate_roughness_pass(self):
        """粗糙度判定通过"""
        from app.core.evaluation_standards import validate_result
        passed, msg = validate_result("rough", {"Ra": 10.0})
        assert passed is True
        assert "Ra" in msg

    def test_validate_roughness_fail(self):
        """粗糙度判定不通过"""
        from app.core.evaluation_standards import validate_result
        passed, msg = validate_result("rough", {"Ra": 20.0})
        assert passed is False
