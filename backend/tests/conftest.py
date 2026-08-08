"""BPLab Trace LIMS Backend — Test Fixtures

Usage:
    cd backend && uvicorn app.main:app --port 8000 &
    pytest tests/ -v --tb=short
"""
from __future__ import annotations

import os
import sys
import asyncio

# Fix for Python 3.14+ on Windows: force SelectorEventLoop to avoid proactor issues
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import pytest
from app.core.security import create_access_token

BASE_URL = "http://localhost:8000"

USERS: dict[str, dict[str, str]] = {
    "admin":    {"role": "管理员"},
    "receiver": {"role": "样品管理员"},
    "tester":   {"role": "实验员"},
    "reviewer": {"role": "复核员"},
    "quality":  {"role": "质量负责人"},
}


def _make_headers(username: str) -> dict[str, str]:
    token = create_access_token(
        data={"sub": username, "role": USERS.get(username, {}).get("role", "")}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        yield c

@pytest.fixture(scope="module")
def admin_headers():
    return _make_headers("admin")

@pytest.fixture(scope="module")
def tester_headers():
    return _make_headers("tester")

@pytest.fixture(scope="module")
def reviewer_headers():
    return _make_headers("reviewer")

@pytest.fixture(scope="module")
def quality_headers():
    return _make_headers("quality")

@pytest.fixture(scope="module")
def receiver_headers():
    return _make_headers("receiver")

@pytest.fixture(scope="module")
def admin_token():
    return create_access_token(data={"sub": "admin", "role": "管理员"})
