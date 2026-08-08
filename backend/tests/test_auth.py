"""认证 API 测试"""
from __future__ import annotations

import pytest

class TestLogin:
    """登录接口测试"""

    def test_login_success(self, client):
        """正确的用户名密码应成功登录"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == "admin"
        assert data["role"] == "管理员"
        assert "menus" in data
        assert len(data["menus"]) > 0

    def test_login_wrong_password(self, client):
        """错误密码应返回 401"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong_password_xyz",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在用户应返回 401"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "nonexistent_user_xyz",
            "password": "any_password",
        })
        assert resp.status_code == 401

    def test_login_empty_username(self, client):
        """空用户名应返回 422（Pydantic 校验）"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "",
            "password": "anything",
        })
        assert resp.status_code == 422

    def test_login_missing_fields(self, client):
        """缺少必填字段应返回 422"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
        })
        assert resp.status_code == 422
class TestMe:
    """当前用户接口测试"""

    def test_me_with_valid_token(self, client, admin_headers):
        """有效 token 应返回用户信息"""
        resp = client.get("/api/v1/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "管理员"

    def test_me_no_token(self, client):
        """无 token 应返回 401 或 403（Bearer 认证失败）"""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    def test_me_invalid_token(self, client):
        """无效 token 应返回 401"""
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid_token_here_xyz",
        })
        assert resp.status_code == 401
class TestSecurity:
    """安全边界测试"""

    def test_sql_injection_login(self, client):
        """SQL 注入尝试不应成功"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin'; DROP TABLE users; --",
            "password": "anything",
        })
        assert resp.status_code == 401  # 使用参数化查询不会成功

    def test_xss_username(self, client):
        """XSS 尝试应被正确处理"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "<script>alert(1)</script>",
            "password": "<img src=x onerror=alert(1)>",
        })
        assert resp.status_code == 401  # 不会执行脚本

    def test_very_long_username(self, client):
        """超长用户名应返回 422"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "a" * 1000,
            "password": "test",
        })
        assert resp.status_code == 422
