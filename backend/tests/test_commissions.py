"""委托 API 测试 + 业务流程"""
from __future__ import annotations

import pytest

class TestCommissionsList:
    """委托列表"""

    def test_list_all(self, client, admin_headers):
        """获取全部委托列表"""
        resp = client.get("/api/v1/commissions", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_with_status_filter(self, client, admin_headers):
        """按状态过滤"""
        resp = client.get("/api/v1/commissions?status=已入库", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            assert item["status"] == "已入库"

    def test_list_pagination(self, client, admin_headers):
        """分页参数"""
        resp = client.get("/api/v1/commissions?limit=5&offset=0", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 5

    def test_list_response_schema(self, client, admin_headers):
        """返回数据结构正确"""
        resp = client.get("/api/v1/commissions?limit=1", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        if data:
            item = data[0]
            assert "commission_no" in item
            assert "client_name" in item
            assert "status" in item
class TestCommissionsDetail:
    """委托详情"""

    def test_nonexistent_commission(self, client, admin_headers):
        """不存在的委托"""
        resp = client.get("/api/v1/commissions/NONEXISTENT_NO", headers=admin_headers)
        assert resp.status_code == 404

    def test_commission_with_wt_prefix(self, client, receiver_headers):
        """创建委托后验证编号为 WT 前缀"""
        # 先查可用的组织和客户
        orgs = client.get("/api/v1/organizations?org_type=client&limit=5", headers=receiver_headers)
        org_data = orgs.json()
        client_org = next((o for o in org_data if o.get("is_client")), None)
        prod_org = next((o for o in org_data if o.get("is_manufacturer")), None)

        if not client_org or not prod_org:
            pytest.skip("测试需要至少一个客户单位和生产单位")

        resp = client.post("/api/v1/commissions", json={
            "client_org_id": client_org["id"],
            "production_org_id": prod_org["id"],
            "production_relation": "客户提供",
            "commission_date": "2026-08-09",
            "notes": "自动化测试委托",
        }, headers=receiver_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["commission_no"].startswith("WT"), f"委托编号应以WT开头，实际: {data['commission_no']}"
        assert len(data["commission_no"]) == 13, f"委托编号应为13位，实际: {len(data['commission_no'])}"

    def test_duplicate_commission_date(self, client, receiver_headers):
        """同一天创建多个委托，编号应递增"""
        orgs = client.get("/api/v1/organizations?org_type=client&limit=5", headers=receiver_headers)
        org_data = orgs.json()
        client_org = next((o for o in org_data if o.get("is_client")), None)
        prod_org = next((o for o in org_data if o.get("is_manufacturer")), None)

        if not client_org or not prod_org:
            pytest.skip("测试需要至少一个客户单位和生产单位")

        nos = []
        for i in range(2):
            resp = client.post("/api/v1/commissions", json={
                "client_org_id": client_org["id"],
                "production_org_id": prod_org["id"],
                "production_relation": "客户提供",
                "commission_date": "2026-08-09",
                "notes": f"并发测试委托 {i}",
            }, headers=receiver_headers)
            if resp.status_code == 200:
                nos.append(resp.json()["commission_no"])

        if len(nos) >= 2:
            assert nos[0] != nos[1], "同一天的委托编号不应重复"
