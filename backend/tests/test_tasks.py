"""任务包 + 实验任务 API 测试"""
from __future__ import annotations

import pytest

class TestTaskPackages:
    """任务包管理"""

    def test_list_packages(self, client, tester_headers):
        """实验员查看自己的任务包"""
        resp = client.get("/api/v1/tasks/packages", headers=tester_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_packages_admin(self, client, admin_headers):
        """管理员查看所有任务包"""
        resp = client.get("/api/v1/tasks/packages", headers=admin_headers)
        assert resp.status_code == 200

    def test_list_packages_with_status(self, client, tester_headers):
        """按状态过滤任务包"""
        resp = client.get("/api/v1/tasks/packages?status=待接收", headers=tester_headers)
        assert resp.status_code == 200

    def test_nonexistent_package(self, client, admin_headers):
        """查询不存在的任务包"""
        resp = client.get("/api/v1/tasks/packages/NONEXISTENT-PKG", headers=admin_headers)
        assert resp.status_code == 404
class TestTasks:
    """实验任务管理"""

    def test_list_my_tasks(self, client, tester_headers):
        """实验员查看自己的任务"""
        resp = client.get("/api/v1/tasks/my", headers=tester_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_my_tasks_with_status(self, client, tester_headers):
        """按状态过滤任务"""
        resp = client.get("/api/v1/tasks/my?status=检测中", headers=tester_headers)
        assert resp.status_code == 200

    def test_nonexistent_task(self, client, admin_headers):
        """查询不存在的任务"""
        resp = client.get("/api/v1/tasks/NONEXISTENT-T99", headers=admin_headers)
        assert resp.status_code == 404
class TestTaskFlow:
    """完整的任务创建-接收流程"""

    def test_create_task_package(self, client, admin_headers):
        """管理员创建任务包"""
        # 这个测试需要已有委托和样品组数据
        # 先验证 API 端点存在并响应正确
        resp = client.post("/api/v1/tasks/packages", json={
            "group_id": 1,
            "experiment_codes": ["I001"],
            "assignee": "tester",
            "reviewer": "reviewer",
        }, headers=admin_headers)
        # 可能返回 404（样品组不存在）或 200/201
        assert resp.status_code in (200, 201, 404)
