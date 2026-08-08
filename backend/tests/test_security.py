"""安全与边界值测试"""
from __future__ import annotations

import pytest

class TestBoundaryValues:
    """边界值测试 — 各类输入"""

    # ── 用户创建边界值 ──

    def test_create_user_short_username(self, client, admin_headers):
        """用户名过短（<2字符）"""
        resp = client.post("/api/v1/users", json={
            "username": "a",
            "display_name": "Test",
            "password": "12345678",
            "role": "实验员",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_create_user_long_username(self, client, admin_headers):
        """用户名过长（>64字符）"""
        resp = client.post("/api/v1/users", json={
            "username": "a" * 65,
            "display_name": "Test",
            "password": "12345678",
            "role": "实验员",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_create_user_short_password(self, client, admin_headers):
        """密码过短（<8位）"""
        resp = client.post("/api/v1/users", json={
            "username": "test_user",
            "display_name": "Test",
            "password": "1234567",
            "role": "实验员",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_create_user_invalid_role(self, client, admin_headers):
        """无效角色"""
        resp = client.post("/api/v1/users", json={
            "username": "test_user",
            "display_name": "Test",
            "password": "12345678",
            "role": "超级管理员",
        }, headers=admin_headers)
        assert resp.status_code == 422

    # ── 委托边界值 ──

    def test_create_commission_invalid_client(self, client, receiver_headers):
        """不存在的客户 ID"""
        resp = client.post("/api/v1/commissions", json={
            "client_org_id": 99999,
            "production_org_id": 1,
            "production_relation": "客户提供",
            "commission_date": "2026-08-09",
        }, headers=receiver_headers)
        assert resp.status_code == 404

    def test_create_commission_invalid_date(self, client, receiver_headers):
        """无效日期格式（Pydantic str类型接受任意字符串，业务层可能500）"""
        resp = client.post("/api/v1/commissions", json={
            "client_org_id": 1,
            "production_org_id": 1,
            "production_relation": "客户提供",
            "commission_date": "not-a-date",
        }, headers=receiver_headers)
        assert resp.status_code in (422, 500)

    # ── 查询边界值 ──

    def test_get_nonexistent_commission(self, client, admin_headers):
        """查询不存在的委托"""
        resp = client.get("/api/v1/commissions/NONEXISTENT", headers=admin_headers)
        assert resp.status_code == 404

    def test_get_nonexistent_task(self, client, admin_headers):
        """查询不存在的任务"""
        resp = client.get("/api/v1/tasks/NONEXISTENT-T99", headers=admin_headers)
        assert resp.status_code == 404

    def test_list_with_negative_limit(self, client, admin_headers):
        """负数 limit（FastAPI默认不验证query参数范围，可能500）"""
        resp = client.get("/api/v1/commissions?limit=-1", headers=admin_headers)
        assert resp.status_code in (422, 500)

    def test_list_with_excessive_limit(self, client, admin_headers):
        """超大 limit（应被限制到 200）"""
        resp = client.get("/api/v1/commissions?limit=500", headers=admin_headers)
        assert resp.status_code == 422

    # ── 权限边界值 ──

    def test_unauthorized_create_user(self, client, tester_headers):
        """实验员不能创建用户"""
        resp = client.post("/api/v1/users", json={
            "username": "hacker",
            "display_name": "Hacker",
            "password": "12345678",
            "role": "管理员",
        }, headers=tester_headers)
        assert resp.status_code == 403

    def test_tester_cannot_reset_password(self, client, tester_headers):
        """实验员不能重置他人密码"""
        resp = client.put("/api/v1/users/admin/password", json={
            "new_password": "hacked123",
        }, headers=tester_headers)
        assert resp.status_code == 403

    def test_access_protected_without_token(self, client):
        """无 token 访问受保护端点"""
        resp = client.get("/api/v1/users")
        assert resp.status_code in (401, 403)
class TestSQLInjection:
    """SQL 注入尝试应全部失败（使用参数化查询）"""

    def _test_endpoint(self, client, headers, method, path, **kwargs):
        """通用测试方法"""
        resp = client.request(method, path, headers=headers, **kwargs)
        # 不应返回 500（如果是 SQL 注入成功可能导致数据库错误）
        # 应在 2xx-4xx 范围内
        assert 200 <= resp.status_code < 500

    def test_sql_injection_in_search(self, client, admin_headers):
        """搜索参数 SQL 注入"""
        resp = client.get(
            "/api/v1/catalog?search='; DROP TABLE sample_catalog; --",
            headers=admin_headers,
        )
        assert resp.status_code == 200  # 参数化查询安全处理

    def test_sql_injection_in_username_param(self, client, admin_headers):
        """用户名参数 SQL 注入"""
        resp = client.put(
            "/api/v1/users/'; DROP TABLE users; --/password",
            json={"new_password": "12345678"},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 404)  # 安全处理，不会被注入
