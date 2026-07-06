"""E2E Tests — API-Level Fixture。

使用 pytest-httpx 对 FastAPI 后端进行 HTTP 层 E2E 测试。
适用于：微信小程序 + Flutter 客户端场景（后端 API 优先）。

用法：
    pytest backend/tests/e2e/ -v

依赖：
    - pytest-httpx（已在 pyproject.toml dev 依赖中）
    - FastAPI app（通过 backend.app.main 导入）
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-e2e-at-least-32-chars!")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


@pytest.fixture(scope="session")
def base_url() -> str:
    """E2E 测试目标 base URL（可被 httpx_recursive 等工具覆写）。"""
    return os.environ.get("E2E_BASE_URL", "http://testserver")


@pytest.fixture(scope="session")
def app():
    """导入 FastAPI app 实例（单例，整个测试 session 共享）。"""
    from backend.app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="session")
def app_config():
    """确保测试配置已加载（set_env 后首次 import）。"""
    from backend.app.conf.app_config import app_config

    return app_config


@pytest.fixture
async def async_client(app) -> AsyncClient:
    """异步 HTTP 客户端，直接调用 ASGI app（无需真实服务器）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def sync_client(app):
    """同步 HTTP 客户端（用于不需要 async 的简单场景）。"""
    from httpx import Client

    transport = ASGITransport(app=app)
    with Client(transport=transport, base_url="http://testserver") as client:
        yield client
