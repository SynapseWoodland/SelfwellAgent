"""E2E Tests — Healthz API 探针。

测试场景：
1. 正常路径：/healthz 返回 200 + status=ok
2. 降级路径：LLM 不可达时返回 200 + status=degraded
3. 宕机路径：DB/Redis 不可达时返回 503
4. 并发：三个探针并发执行（验证 asyncio.gather）
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
class TestHealthzAPI:
    """E2E: /healthz 探针端点."""

    async def test_healthz_returns_200_ok(self, async_client):
        """正常路径：所有依赖可达 → HTTP 200 + status=ok."""
        response = await async_client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "checks" in data
        assert "db" in data["checks"]
        assert "redis" in data["checks"]
        assert "llm" in data["checks"]

    async def test_healthz_degraded_when_llm_down(self, async_client):
        """降级路径：LLM 不可达 → HTTP 200 + status=degraded."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            return_value="ok",
        ), patch(
            "app.api.routers.system._probe_redis",
            new_callable=AsyncMock,
            return_value="ok",
        ), patch(
            "app.api.routers.system._probe_llm",
            new_callable=AsyncMock,
            return_value="degraded",
        ):
            response = await async_client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"

    async def test_healthz_503_when_db_down(self, async_client):
        """宕机路径：PostgreSQL 不可达 → HTTP 503."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            return_value="down",
        ), patch(
            "app.api.routers.system._probe_redis",
            new_callable=AsyncMock,
            return_value="ok",
        ), patch(
            "app.api.routers.system._probe_llm",
            new_callable=AsyncMock,
            return_value="ok",
        ):
            response = await async_client.get("/healthz")
        assert response.status_code == 503
        assert response.json()["status"] == "down"

    async def test_healthz_503_when_redis_down(self, async_client):
        """宕机路径：Redis 不可达 → HTTP 503."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            return_value="ok",
        ), patch(
            "app.api.routers.system._probe_redis",
            new_callable=AsyncMock,
            return_value="down",
        ), patch(
            "app.api.routers.system._probe_llm",
            new_callable=AsyncMock,
            return_value="ok",
        ):
            response = await async_client.get("/healthz")
        assert response.status_code == 503
        assert response.json()["status"] == "down"

    async def test_healthz_response_headers(self, async_client):
        """验证响应头包含 trace context."""
        response = await async_client.get("/healthz")
        assert response.status_code == 200
        # TraceContextMiddleware 应设置 X-Request-ID
        assert "x-request-id" in {k.lower() for k in response.headers.keys()}

    async def test_healthz_probe_concurrency(self, async_client):
        """验证三个探针并发执行（总时间应接近最慢探针，非累加）。"""
        import asyncio
        from unittest.mock import AsyncMock, patch

        probe_log: list = []

        async def logged_probe(delay: float, result: str):
            await asyncio.sleep(delay)
            probe_log.append(result)
            return result

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            side_effect=lambda: logged_probe(0.05, "ok"),
        ), patch(
            "app.api.routers.system._probe_redis",
            new_callable=AsyncMock,
            side_effect=lambda: logged_probe(0.05, "ok"),
        ), patch(
            "app.api.routers.system._probe_llm",
            new_callable=AsyncMock,
            side_effect=lambda: logged_probe(0.05, "ok"),
        ):
            import time

            start = time.monotonic()
            response = await async_client.get("/healthz")
            elapsed = time.monotonic() - start
        assert response.status_code == 200
        # 三个 50ms 探针并发执行，总时间应 < 150ms
        assert elapsed < 0.15, f"探针未并发执行，耗时 {elapsed:.3f}s"
        assert len(probe_log) == 3
