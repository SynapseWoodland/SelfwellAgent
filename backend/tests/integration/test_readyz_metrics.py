"""Integration test — /readyz 探针（Phase 4 · 批次 4 新增）。

真源：
- ``docs/plan/backend-fix-plan.md`` 批次 4 §「健康检查端点增强」
- ``backend/app/api/routers/system.py``

测试场景：
1. 正常路径：db + redis 都 ok → HTTP 200 + status=ready
2. db down → HTTP 503 + status=not_ready
3. redis down → HTTP 503 + status=not_ready
4. readyz 不查 LLM / MinIO（与 /healthz 区别）
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────────────────────────────────────
# §一 Fixture：替换探针函数
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def ready_probes_ok() -> Iterator[None]:
    """db + redis 都 ok → ready."""
    with (
        patch("app.api.routers.system._probe_db_timed", return_value=("ok", 1.0)),
        patch("app.api.routers.system._probe_redis_timed", return_value=("ok", 0.5)),
    ):
        yield


@pytest.fixture
def ready_db_down() -> Iterator[None]:
    """db down → not_ready."""
    with (
        patch("app.api.routers.system._probe_db_timed", return_value=("down", 2000.0)),
        patch("app.api.routers.system._probe_redis_timed", return_value=("ok", 0.5)),
    ):
        yield


@pytest.fixture
def ready_redis_down() -> Iterator[None]:
    """redis down → not_ready."""
    with (
        patch("app.api.routers.system._probe_db_timed", return_value=("ok", 1.0)),
        patch("app.api.routers.system._probe_redis_timed", return_value=("down", 2000.0)),
    ):
        yield


# ──────────────────────────────────────────────────────────────────────────────
# §二 测试用例
# ──────────────────────────────────────────────────────────────────────────────
def test_readyz_all_ok_returns_200(ready_probes_ok: None) -> None:
    """db + redis ok → status=ready，HTTP 200。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"db": "ok", "redis": "ok"}


def test_readyz_db_down_returns_503(ready_db_down: None) -> None:
    """db down → status=not_ready，HTTP 503。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["db"] == "down"


def test_readyz_redis_down_returns_503(ready_redis_down: None) -> None:
    """redis down → status=not_ready，HTTP 503。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["redis"] == "down"


def test_readyz_ignores_llm_degradation() -> None:
    """readyz 不查 LLM —— 即便 LLM degraded，db+redis ok → ready。

    与 /healthz 区别：readyz 只关心 readiness，不应被 LLM 抖动拉走流量。
    """
    from app.main import app

    with (
        patch("app.api.routers.system._probe_db_timed", return_value=("ok", 1.0)),
        patch("app.api.routers.system._probe_redis_timed", return_value=("ok", 0.5)),
        patch("app.api.routers.system._probe_llm", return_value="degraded"),
        patch("app.api.routers.system._probe_minio", return_value="degraded"),
    ):
        with TestClient(app) as client:
            response = client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "llm" not in body["checks"]  # readyz 不查 LLM
    assert "minio" not in body["checks"]  # readyz 不查 MinIO


# ──────────────────────────────────────────────────────────────────────────────
# §三 /metrics 端点
# ──────────────────────────────────────────────────────────────────────────────
def test_metrics_endpoint_exposes_prometheus_format() -> None:
    """GET /metrics 返回 Prometheus exposition format（text/plain; version=0.0.4）。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    # Prometheus exposition format 包含 HELP/TYPE 注释行
    body = response.text
    # 至少包含一个 selfwell_* 指标
    assert "selfwell_" in body, f"/metrics 响应缺 selfwell_* 指标: {body[:500]}"
    # Content-Type 必须含 text/plain
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type, f"Content-Type 错: {content_type}"


def test_metrics_includes_smart_analyze_counter() -> None:
    """smart_analyze_done_total 计数器已在 registry 注册（即使值为 0 也会暴露）。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    # 关键指标存在
    assert "selfwell_smart_analyze_done_total" in body, (
        "/metrics 缺 selfwell_smart_analyze_done_total"
    )
    assert "selfwell_llm_cost_yuan_total" in body, (
        "/metrics 缺 selfwell_llm_cost_yuan_total"
    )
    assert "selfwell_sse_events_total" in body, (
        "/metrics 缺 selfwell_sse_events_total"
    )