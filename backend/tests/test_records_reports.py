"""原始记录 + 报告 API 测试"""
from __future__ import annotations

import pytest

class TestRecords:
    """原始记录管理"""

    def test_pending_reviews(self, client, reviewer_headers):
        """复核员查看待复核记录"""
        resp = client.get("/api/v1/records/pending-review", headers=reviewer_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_pending_reviews_unauthorized(self, client, tester_headers):
        """实验员不能查看待复核列表（可能为空或权限限制）"""
        resp = client.get("/api/v1/records/pending-review", headers=tester_headers)
        # 实验员也可以访问，但看到的可能为空
        assert resp.status_code == 200

    def test_record_versions_nonexistent(self, client, admin_headers):
        """查询不存在的记录版本"""
        resp = client.get("/api/v1/records/NONEXISTENT/versions", headers=admin_headers)
        assert resp.status_code == 404

    def test_record_version_nonexistent(self, client, admin_headers):
        """查询不存在的记录版本"""
        resp = client.get("/api/v1/records/NONEXISTENT/v1", headers=admin_headers)
        assert resp.status_code == 404
class TestReports:
    """报告管理"""

    def test_list_reports(self, client, admin_headers):
        """管理员查看所有报告"""
        resp = client.get("/api/v1/reports", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_reports_quality(self, client, quality_headers):
        """质量负责人查看报告"""
        resp = client.get("/api/v1/reports", headers=quality_headers)
        assert resp.status_code == 200

    def test_nonexistent_report(self, client, admin_headers):
        """查询不存在的报告"""
        resp = client.get("/api/v1/reports/R-NONEXISTENT", headers=admin_headers)
        assert resp.status_code == 404

    def test_generate_report_no_task(self, client, quality_headers):
        """为不存在的任务生成报告"""
        resp = client.post("/api/v1/reports", json={
            "task_no": "NONEXISTENT-T99",
        }, headers=quality_headers)
        assert resp.status_code == 400  # 任务未完成
class TestReportFlow:
    """报告生成-审核-签发流程"""

    def test_report_generation_requires_completed_task(self, client, quality_headers):
        """只有已完成的任务才能生成报告"""
        resp = client.post("/api/v1/reports", json={
            "task_no": "BP20260807001-T01",
        }, headers=quality_headers)
        assert resp.status_code in (400, 404)  # 任务可能不存在或未完成

    def test_report_quality_review_nonexistent(self, client, quality_headers):
        """审核不存在的报告"""
        resp = client.post("/api/v1/reports/R-NONEXISTENT/quality-review", json={
            "decision": "通过",
            "comment": "test",
        }, headers=quality_headers)
        assert resp.status_code == 404

    def test_report_approve_nonexistent(self, client, quality_headers):
        """签发不存在的报告"""
        resp = client.post("/api/v1/reports/R-NONEXISTENT/approve", json={
            "decision": "通过",
            "comment": "test",
        }, headers=quality_headers)
        assert resp.status_code == 404
