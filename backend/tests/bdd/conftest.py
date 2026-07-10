"""Pytest configuration — BDD 行为驱动测试 fixtures。

bdd/test_bdd_healthz.py 等 Gherkin feature 测试需要 FastAPI TestClient 同步 fixture。
本 conftest 提供与 e2e/conftest.py 兼容的 fixture 接口。

V5.2.1-PR0.x: 新建 — 修 PR0 报告 bdd module 5 ERROR（fixture 'client' not found）。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-bdd-at-least-32-chars!")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


@pytest.fixture(scope="session")
def app():
    """导入 FastAPI app 实例（单例，整个 bdd session 共享）。"""
    from backend.app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    """同步 FastAPI TestClient（用于 given-when-then Gherkin 风格 BDD 测试）。"""
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
