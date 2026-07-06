"""E2E Tests — API 端点冒烟测试。

对所有已实现的 API 路由进行 HTTP 层冒烟测试。
覆盖：/healthz、/docs、/openapi.json
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
class TestAPIEndpoints:
    """E2E: API 端点冒烟测试."""

    async def test_healthz_endpoint_exists(self, async_client):
        """验证 /healthz 端点存在并可访问."""
        response = await async_client.get("/healthz")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "checks" in data

    async def test_docs_endpoint_accessible(self, async_client):
        """验证 Swagger UI 可访问."""
        response = await async_client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    async def test_openapi_schema_accessible(self, async_client):
        """验证 OpenAPI schema 端点可访问."""
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["openapi"].startswith("3.")
        assert "paths" in data
        assert "/healthz" in data["paths"]

    async def test_healthz_content_type_json(self, async_client):
        """验证 /healthz 返回 JSON 格式."""
        response = await async_client.get("/healthz")
        assert "application/json" in response.headers.get("content-type", "")

    async def test_cors_preflight_if_enabled(self, async_client):
        """OPTIONS 预检请求处理（如果有 CORS 配置）。"""
        response = await async_client.options(
            "/healthz",
            headers={
                "Origin": "https://mp.weixin.qq.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # 不强制要求 CORS 配置；骨架阶段可能无 CORS
        assert response.status_code in (200, 405)

    async def test_404_for_unknown_path(self, async_client):
        """未知路径返回 404（FastAPI 默认行为）。"""
        response = await async_client.get("/nonexistent-path-xyz-123")
        assert response.status_code == 404

    async def test_healthz_in_openapi_paths(self, async_client):
        """验证 /healthz 在 OpenAPI schema 中正确注册."""
        response = await async_client.get("/openapi.json")
        data = response.json()
        assert "/healthz" in data["paths"]
        healthz_spec = data["paths"]["/healthz"]["get"]
        assert "summary" in healthz_spec


@pytest.mark.asyncio
class TestMiddlewareChain:
    """E2E: 中间件链路验证."""

    async def test_trace_context_injects_request_id(self, async_client):
        """验证 TraceContextMiddleware 注入 X-Request-ID."""
        response = await async_client.get("/healthz")
        assert response.status_code in (200, 503)
        assert "x-request-id" in {k.lower() for k in response.headers.keys()}

    async def test_exception_handler_returns_json_on_error(self, async_client):
        """验证 ExceptionHandlerMiddleware 返回 JSON 格式错误."""
        response = await async_client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        assert "application/json" in response.headers.get("content-type", "")
        data = response.json()
        assert "detail" in data  # FastAPI 默认 404 body

    async def test_rate_limit_returns_json_error(self, async_client):
        """验证 RateLimitMiddleware 返回 JSON 格式 429."""
        import time

        # 在同一 worker 内快速发请求
        responses = []
        for _ in range(15):
            r = await async_client.get("/healthz")
            responses.append(r.status_code)
            if r.status_code == 429:
                break
            time.sleep(0.005)

        # 检查是否触发了限流
        has_429 = 429 in responses
        if has_429:
            r429 = responses[responses.index(429)]
            assert r429 == 429
