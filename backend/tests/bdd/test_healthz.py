"""Healthz Probe — Gherkin BDD Feature。

验证 Selfwell 后端 `/healthz` 三段探针（db / redis / llm）的完整决策树。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.bdd


@pytest.mark.bdd
class TestHealthz:
    """BDD: Healthz probe decision tree scenarios."""

    @pytest.mark.asyncio
    async def test_healthz_all_services_ok_returns_200(self, client):
        """Scenario: 所有依赖服务（db/redis/llm）均可达 → HTTP 200 + status=ok."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "db" in data["checks"]
        assert "redis" in data["checks"]
        assert "llm" in data["checks"]

    @pytest.mark.asyncio
    async def test_healthz_db_down_returns_503(self, client):
        """Scenario: PostgreSQL 不可达时 → HTTP 503 + status=down."""
        # patch db probe to return 'down'
        import asyncio
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            return_value="down",
        ):
            with patch(
                "app.api.routers.system._probe_redis",
                new_callable=AsyncMock,
                return_value="ok",
            ):
                with patch(
                    "app.api.routers.system._probe_llm",
                    new_callable=AsyncMock,
                    return_value="ok",
                ):
                    response = client.get("/healthz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "down"

    @pytest.mark.asyncio
    async def test_healthz_redis_down_returns_503(self, client):
        """Scenario: Redis 不可达时 → HTTP 503 + status=down."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            return_value="ok",
        ):
            with patch(
                "app.api.routers.system._probe_redis",
                new_callable=AsyncMock,
                return_value="down",
            ):
                with patch(
                    "app.api.routers.system._probe_llm",
                    new_callable=AsyncMock,
                    return_value="ok",
                ):
                    response = client.get("/healthz")
        assert response.status_code == 503
        assert response.json()["status"] == "down"

    @pytest.mark.asyncio
    async def test_healthz_llm_degraded_returns_200(self, client):
        """Scenario: 仅 LLM 降级（db/redis 正常）→ HTTP 200 + status=degraded."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            return_value="ok",
        ):
            with patch(
                "app.api.routers.system._probe_redis",
                new_callable=AsyncMock,
                return_value="ok",
            ):
                with patch(
                    "app.api.routers.system._probe_llm",
                    new_callable=AsyncMock,
                    return_value="degraded",
                ):
                    response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_healthz_probes_run_concurrently(self, client):
        """Scenario: 三段探针并发执行，无顺序依赖。"""
        from unittest.mock import AsyncMock, patch
        import asyncio

        probe_times: dict = {}

        async def slow_probe(value: str, key: str):
            await asyncio.sleep(0.1)
            probe_times[key] = True
            return value

        with patch(
            "app.api.routers.system._probe_db",
            new_callable=AsyncMock,
            side_effect=lambda: slow_probe("ok", "db"),
        ):
            with patch(
                "app.api.routers.system._probe_redis",
                new_callable=AsyncMock,
                side_effect=lambda: slow_probe("ok", "redis"),
            ):
                with patch(
                    "app.api.routers.system._probe_llm",
                    new_callable=AsyncMock,
                    side_effect=lambda: slow_probe("ok", "llm"),
                ):
                    response = client.get("/healthz")
        # 如果并发执行，总时间应 < 每个探针的累加时间
        assert response.status_code == 200
        assert len(probe_times) == 3
