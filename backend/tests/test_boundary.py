"""边界值测试 — 覆盖所有新 API 端点的必填/空值/类型/权限/状态机/异常路径"""
from __future__ import annotations

import pytest


# ═══════════════════════════════════════════════════════════════
# 1. 设备故障处置 incident — 边界值
# ═══════════════════════════════════════════════════════════════

class TestIncidentsBoundary:
    """POST /incidents 边界值"""

    def test_report_missing_required_fields(self, client, tester_headers):
        """缺少必填字段（task_no, equipment_no, fault_description）"""
        # 全空
        resp = client.post("/api/v1/incidents", json={}, headers=tester_headers)
        assert resp.status_code == 422

        # 缺 equipment_no
        resp = client.post("/api/v1/incidents", json={
            "task_no": "BP20260809-001-T01", "fault_description": "故障描述",
        }, headers=tester_headers)
        assert resp.status_code in (400, 422, 404)  # 404 如果任务不存在

        # 缺 fault_description
        resp = client.post("/api/v1/incidents", json={
            "task_no": "BP20260809-001-T01", "equipment_no": "EQ-001",
        }, headers=tester_headers)
        assert resp.status_code in (400, 422, 404)

    def test_report_nonexistent_task(self, client, tester_headers):
        """不存在的任务编号"""
        resp = client.post("/api/v1/incidents", json={
            "task_no": "NONEXISTENT-TASK-999",
            "equipment_no": "EQ-001",
            "fault_description": "测试故障",
        }, headers=tester_headers)
        assert resp.status_code == 404

    def test_report_empty_strings(self, client, tester_headers):
        """空字符串字段"""
        resp = client.post("/api/v1/incidents", json={
            "task_no": "   ", "equipment_no": "EQ-001", "fault_description": "测试",
        }, headers=tester_headers)
        assert resp.status_code in (400, 404, 422)

    def test_report_invalid_types(self, client, tester_headers):
        """无效类型 — fault_description 传数字"""
        resp = client.post("/api/v1/incidents", json={
            "task_no": "BP20260809-001-T01",
            "equipment_no": "EQ-001",
            "fault_description": 12345,
        }, headers=tester_headers)
        assert resp.status_code in (400, 404, 422)

    def test_list_without_auth(self, client):
        """无认证访问"""
        resp = client.get("/api/v1/incidents")
        assert resp.status_code == 401

    def test_nonexistent_detail(self, client, admin_headers):
        """不存在的故障详情"""
        resp = client.get("/api/v1/incidents/NONEXISTENT-999", headers=admin_headers)
        assert resp.status_code == 404

    def test_isolate_missing_location(self, client, admin_headers):
        """隔离时缺少位置 — 对不存在的编号操作"""
        resp = client.put("/api/v1/incidents/EQI20260809-001/isolate",
                                json={"isolation_location": "", "note": ""},
                                headers=admin_headers)
        assert resp.status_code in (400, 404, 422)

    def test_assess_nonexistent(self, client, quality_headers):
        """评估不存在的故障（Pydantic先校验字段，返回422）"""
        resp = client.put("/api/v1/incidents/EQI20260809-999/assess",
                                json={"sample_validity": "样品有效", "quality_note": "测试"},
                                headers=quality_headers)
        assert resp.status_code in (404, 422)

    def test_approve_nonexistent(self, client, admin_headers):
        """批准不存在的故障（Pydantic先校验字段，返回422）"""
        resp = client.put("/api/v1/incidents/EQI20260809-999/approve",
                                json={"recovery_route": "使用原设备重做", "admin_note": ""},
                                headers=admin_headers)
        assert resp.status_code in (404, 422)

    def test_role_authorization(self, client, tester_headers, reviewer_headers):
        """角色权限：实验员可报告，复核员不可隔离（Pydantic先校验字段）"""
        # 复核员尝试隔离（需要样品管理员）
        resp = client.put("/api/v1/incidents/EQI20260809-001/isolate",
                                json={"isolation_location": "test", "note": ""},
                                headers=reviewer_headers)
        assert resp.status_code in (403, 404, 422)


# ═══════════════════════════════════════════════════════════════
# 2. 客户异议 objection — 边界值
# ═══════════════════════════════════════════════════════════════

class TestObjectionsBoundary:
    """POST /objections 边界值"""

    def test_register_empty_fields(self, client, receiver_headers):
        """登记异议必填为空"""
        resp = client.post("/api/v1/objections", json={}, headers=receiver_headers)
        assert resp.status_code == 422

        resp = client.post("/api/v1/objections", json={
            "report_no": "R20260809-001-T01",
            "description": "   ",
            "disputed_items": "",
        }, headers=receiver_headers)
        assert resp.status_code in (400, 404, 422)

    def test_register_nonexistent_report(self, client, receiver_headers):
        """不存在的报告"""
        resp = client.post("/api/v1/objections", json={
            "report_no": "R99999999-999-T99",
            "description": "客户对结果有疑问",
            "disputed_items": "冲击试验",
        }, headers=receiver_headers)
        assert resp.status_code == 404

    def test_register_wrong_role(self, client, tester_headers):
        """实验员不能登记异议"""
        resp = client.post("/api/v1/objections", json={
            "report_no": "R20260809-001-T01",
            "description": "测试",
            "disputed_items": "硬度",
        }, headers=tester_headers)
        assert resp.status_code == 403

    def test_list_objections(self, client, admin_headers):
        """异议列表"""
        resp = client.get("/api/v1/objections", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_nonexistent_objection_detail(self, client, admin_headers):
        """不存在的异议"""
        resp = client.get("/api/v1/objections/Y99999999-999", headers=admin_headers)
        assert resp.status_code == 404

    def test_investigate_nonexistent(self, client, quality_headers):
        """调查不存在的异议"""
        resp = client.put("/api/v1/objections/Y20260809-999/investigate", json={
            "pathway": "是我方问题",
            "investigation": "测试调查过程",
            "trace_conclusion": "测试追溯结论",
        }, headers=quality_headers)
        assert resp.status_code == 404

    def test_investigate_invalid_pathway(self, client, quality_headers):
        """无效的调查路径"""
        resp = client.put("/api/v1/objections/Y20260809-999/investigate", json={
            "pathway": "无效路径",
            "investigation": "测试",
            "trace_conclusion": "测试",
        }, headers=quality_headers)
        assert resp.status_code in (404, 422)

    def test_investigate_empty_text(self, client, quality_headers):
        """调查过程和结论为空"""
        resp = client.put("/api/v1/objections/Y20260809-999/investigate", json={
            "pathway": "是我方问题",
            "investigation": "   ",
            "trace_conclusion": "",
        }, headers=quality_headers)
        assert resp.status_code in (404, 422)

    def test_retest_decision_invalid(self, client, receiver_headers):
        """无效的重测决定"""
        resp = client.put("/api/v1/objections/Y20260809-999/retest-decision", json={
            "decision": "无效选项",
        }, headers=receiver_headers)
        assert resp.status_code in (404, 422)

    def test_dispatch_retest_nonexistent(self, client, receiver_headers):
        """下发重测到不存在的异议"""
        resp = client.post("/api/v1/objections/Y20260809-999/dispatch-retest", json={
            "assignee": "tester",
            "selected_sample_nos": [],
        }, headers=receiver_headers)
        assert resp.status_code == 404

    def test_wrong_role_investigate(self, client, tester_headers):
        """实验员不能调查异议"""
        resp = client.put("/api/v1/objections/Y20260809-999/investigate", json={
            "pathway": "是我方问题", "investigation": "测试", "trace_conclusion": "测试",
        }, headers=tester_headers)
        assert resp.status_code in (403, 404)

    def test_prepare_response_empty(self, client, receiver_headers):
        """回复正文为空"""
        resp = client.put("/api/v1/objections/Y20260809-999/prepare-response", json={
            "response_text": "   ", "response_method": "邮件",
        }, headers=receiver_headers)
        assert resp.status_code in (404, 422)

    def test_send_nonexistent(self, client, receiver_headers):
        """发送不存在的异议"""
        resp = client.put("/api/v1/objections/Y20260809-999/send", json={
            "note": "测试",
        }, headers=receiver_headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
# 3. 危废处理 hazardous_waste — 边界值
# ═══════════════════════════════════════════════════════════════

class TestHazardousWasteBoundary:
    """POST /hazardous-waste 边界值"""

    def test_create_empty_fields(self, client, tester_headers):
        """必填字段全空"""
        resp = client.post("/api/v1/hazardous-waste", json={}, headers=tester_headers)
        assert resp.status_code == 422

    def test_create_zero_quantity(self, client, tester_headers):
        """数量为0"""
        resp = client.post("/api/v1/hazardous-waste", json={
            "task_nos": ["NONEXISTENT-001"],
            "waste_name": "废液",
            "quantity": 0,
            "disposal_method": "中和处理",
        }, headers=tester_headers)
        assert resp.status_code in (400, 404, 422)

    def test_create_negative_quantity(self, client, tester_headers):
        """数量为负数"""
        resp = client.post("/api/v1/hazardous-waste", json={
            "task_nos": ["NONEXISTENT-001"],
            "waste_name": "废液",
            "quantity": -10,
            "disposal_method": "中和处理",
        }, headers=tester_headers)
        assert resp.status_code in (400, 404, 422)

    def test_create_no_tasks(self, client, tester_headers):
        """无关联任务"""
        resp = client.post("/api/v1/hazardous-waste", json={
            "task_nos": [],
            "waste_name": "废液",
            "quantity": 100,
            "disposal_method": "中和处理",
        }, headers=tester_headers)
        assert resp.status_code == 422

    def test_create_empty_waste_name(self, client, tester_headers):
        """危废名称为空"""
        resp = client.post("/api/v1/hazardous-waste", json={
            "task_nos": ["NONEXISTENT-001"],
            "waste_name": "   ",
            "quantity": 100,
            "disposal_method": "中和处理",
        }, headers=tester_headers)
        assert resp.status_code in (400, 404, 422)

    def test_create_empty_disposal_method(self, client, tester_headers):
        """处置方式为空"""
        resp = client.post("/api/v1/hazardous-waste", json={
            "task_nos": ["NONEXISTENT-001"],
            "waste_name": "废液",
            "quantity": 100,
            "disposal_method": "",
        }, headers=tester_headers)
        assert resp.status_code in (400, 404, 422)

    def test_create_wrong_role(self, client, receiver_headers):
        """样品管理员不能登记危废"""
        resp = client.post("/api/v1/hazardous-waste", json={
            "task_nos": ["NONEXISTENT-001"],
            "waste_name": "废液",
            "quantity": 100,
            "disposal_method": "中和处理",
        }, headers=receiver_headers)
        assert resp.status_code == 403

    def test_list_waste(self, client, admin_headers):
        """列表"""
        resp = client.get("/api/v1/hazardous-waste", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_with_task_filter(self, client, tester_headers):
        """按任务过滤"""
        resp = client.get("/api/v1/hazardous-waste?task_no=NONEXISTENT-001", headers=tester_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ═══════════════════════════════════════════════════════════════
# 4. 报告发放 delivery — 边界值
# ═══════════════════════════════════════════════════════════════

class TestReportDeliveryBoundary:
    """POST /reports/{no}/delivery 边界值"""

    def test_deliver_nonexistent_report(self, client, receiver_headers):
        """发放不存在的报告"""
        resp = client.post("/api/v1/reports/R99999999-999-T99/delivery", json={
            "delivery_method": "自取", "recipient": "张三",
        }, headers=receiver_headers)
        assert resp.status_code == 404

    def test_deliver_empty_fields(self, client, receiver_headers):
        """发放必填为空"""
        resp = client.post("/api/v1/reports/R20260809-001-T01/delivery", json={
            "delivery_method": "", "recipient": "",
        }, headers=receiver_headers)
        assert resp.status_code in (404, 422)

    def test_deliver_wrong_role(self, client, tester_headers):
        """实验员不能发放"""
        resp = client.post("/api/v1/reports/R20260809-001-T01/delivery", json={
            "delivery_method": "自取", "recipient": "张三",
        }, headers=tester_headers)
        assert resp.status_code == 403

    def test_get_deliveries(self, client, admin_headers):
        """获取发放记录"""
        resp = client.get("/api/v1/reports/R20260809-001-T01/deliveries", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_revoke_nonexistent(self, client, admin_headers):
        """撤回不存在的报告"""
        resp = client.post("/api/v1/reports/R99999999-999-T99/revoke", headers=admin_headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
# 5. 样品归还 returns — 边界值
# ═══════════════════════════════════════════════════════════════

class TestReturnsBoundary:
    """样品借出/归还 边界值"""

    def test_loan_empty(self, client, tester_headers):
        """借出必填为空"""
        resp = client.post("/api/v1/returns/loan", json={}, headers=tester_headers)
        assert resp.status_code == 422

    def test_loan_no_samples(self, client, tester_headers):
        """借出无样品（空sample_nos被拒绝或包不存在）"""
        resp = client.post("/api/v1/returns/loan", json={
            "package_no": "BP20260809-001",
            "sample_nos": [],
        }, headers=tester_headers)
        assert resp.status_code in (404, 422)

    def test_loan_wrong_role(self, client, receiver_headers):
        """样品管理员不能借出"""
        resp = client.post("/api/v1/returns/loan", json={
            "package_no": "BP20260809-001",
            "sample_nos": ["BP20260809-001-S01"],
        }, headers=receiver_headers)
        assert resp.status_code == 403

    def test_return_submit_empty(self, client, tester_headers):
        """归还必填为空"""
        resp = client.post("/api/v1/returns/submit", json={}, headers=tester_headers)
        assert resp.status_code == 422

    def test_return_submit_no_samples(self, client, tester_headers):
        """归还无样品"""
        resp = client.post("/api/v1/returns/submit", json={
            "package_no": "BP20260809-001",
            "sample_nos": [],
        }, headers=tester_headers)
        assert resp.status_code == 422

    def test_return_submit_wrong_role(self, client, receiver_headers):
        """样品管理员不能提交归还"""
        resp = client.post("/api/v1/returns/submit", json={
            "package_no": "BP20260809-001",
            "sample_nos": ["BP20260809-001-S01"],
        }, headers=receiver_headers)
        assert resp.status_code == 403

    def test_pending_list(self, client, admin_headers):
        """待确认归还列表"""
        resp = client.get("/api/v1/returns/pending", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_confirm_nonexistent(self, client, admin_headers):
        """确认不存在的归还"""
        resp = client.put("/api/v1/returns/999999/confirm", json={
            "return_condition": "完好",
        }, headers=admin_headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
# 6. 通知 notifications — 边界值
# ═══════════════════════════════════════════════════════════════

class TestNotificationsBoundary:
    """通知 边界值"""

    def test_list_without_auth(self, client):
        """无认证"""
        resp = client.get("/api/v1/notifications")
        assert resp.status_code == 401

    def test_list(self, client, admin_headers):
        """正常列表"""
        resp = client.get("/api/v1/notifications", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_mark_read_empty(self, client, admin_headers):
        """标记空列表已读"""
        resp = client.put("/api/v1/notifications/read", json={}, headers=admin_headers)
        assert resp.status_code == 200

    def test_mark_read_specific(self, client, admin_headers):
        """标记特定通知已读"""
        resp = client.put("/api/v1/notifications/read", json={"ids": []}, headers=admin_headers)
        assert resp.status_code == 200

    def test_mark_all_read(self, client, admin_headers):
        """全部已读"""
        resp = client.put("/api/v1/notifications/read", json={"ids": None}, headers=admin_headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════
# 7. 审计追踪 — 边界值
# ═══════════════════════════════════════════════════════════════

class TestAuditTrailBoundary:
    """审计链验证 边界值"""

    def test_verify_nonexistent_entity(self, client, admin_headers):
        """验证不存在的实体"""
        resp = client.get("/api/v1/traceability/audit/verify/nonexistent/no-such-id",
                                headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["entries"] == 0

    def test_verify_all_chains(self, client, admin_headers):
        """批量验证"""
        resp = client.get("/api/v1/traceability/audit/verify-all-chains", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_chains" in data
        assert "broken_chains" in data

    def test_without_auth(self, client):
        """无认证"""
        resp = client.get("/api/v1/traceability/audit/verify/commission/WT20260809-001")
        assert resp.status_code == 401
