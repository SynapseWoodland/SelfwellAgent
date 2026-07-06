"""Integration test — /healthz 三段探针（db / redis / llm）返回 OK / DEGRADED / DOWN。

PR-1 AC-1 + §6 Schema：
- OK: status=ok, 所有 checks ok → 200
- DEGRADED: status=degraded, llm=degraded → 200
- DOWN: status=down, db=down 或 redis=down → 503
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────────────────────────────────────
# §一 Fixture：替换探针函数，模拟 DB / Redis / LLM 状态
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def probes_ok() -> Iterator[None]:
    """所有探针返回 ok。"""
    with (
        patch("app.api.routers.system._probe_db", return_value="ok"),
        patch("app.api.routers.system._probe_redis", return_value="ok"),
        patch("app.api.routers.system._probe_llm", return_value="ok"),
    ):
        yield


@pytest.fixture
def probes_llm_degraded() -> Iterator[None]:
    """LLM 探针 degraded，其它 ok。"""
    with (
        patch("app.api.routers.system._probe_db", return_value="ok"),
        patch("app.api.routers.system._probe_redis", return_value="ok"),
        patch("app.api.routers.system._probe_llm", return_value="degraded"),
    ):
        yield


@pytest.fixture
def probes_db_down() -> Iterator[None]:
    """DB 探针 down，其它 ok。"""
    with (
        patch("app.api.routers.system._probe_db", return_value="down"),
        patch("app.api.routers.system._probe_redis", return_value="ok"),
        patch("app.api.routers.system._probe_llm", return_value="ok"),
    ):
        yield


@pytest.fixture
def probes_redis_down() -> Iterator[None]:
    """Redis 探针 down，其它 ok。"""
    with (
        patch("app.api.routers.system._probe_db", return_value="ok"),
        patch("app.api.routers.system._probe_redis", return_value="down"),
        patch("app.api.routers.system._probe_llm", return_value="ok"),
    ):
        yield


@pytest.fixture
def probes_all_down() -> Iterator[None]:
    """全部 down。"""
    with (
        patch("app.api.routers.system._probe_db", return_value="down"),
        patch("app.api.routers.system._probe_redis", return_value="down"),
        patch("app.api.routers.system._probe_llm", return_value="down"),
    ):
        yield


# ──────────────────────────────────────────────────────────────────────────────
# §二 OK 场景
# ──────────────────────────────────────────────────────────────────────────────
def test_healthz_all_ok_returns_200(probes_ok: None) -> None:
    """所有探针 ok → status=ok，HTTP 200。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"db": "ok", "redis": "ok", "llm": "ok"}


# ──────────────────────────────────────────────────────────────────────────────
# §三 DEGRADED 场景
# ──────────────────────────────────────────────────────────────────────────────
def test_healthz_llm_degraded_returns_200(probes_llm_degraded: None) -> None:
    """LLM 探针 degraded → status=degraded，HTTP 200（不阻断服务）。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["llm"] == "degraded"
    assert body["checks"]["db"] == "ok"
    assert body["checks"]["redis"] == "ok"


# ──────────────────────────────────────────────────────────────────────────────
# §四 DOWN 场景
# ──────────────────────────────────────────────────────────────────────────────
def test_healthz_db_down_returns_503(probes_db_down: None) -> None:
    """DB 探针 down → status=down，HTTP 503。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "down"
    assert body["checks"]["db"] == "down"


def test_healthz_redis_down_returns_503(probes_redis_down: None) -> None:
    """Redis 探针 down → status=down，HTTP 503。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "down"
    assert body["checks"]["redis"] == "down"


def test_healthz_all_down_returns_503(probes_all_down: None) -> None:
    """全部 down → status=down，HTTP 503。"""
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "down"


# ──────────────────────────────────────────────────────────────────────────────
# §五 探针函数本身的行为契约
# ──────────────────────────────────────────────────────────────────────────────
def test_probe_db_returns_string() -> None:
    """_probe_db 返回值必须是 'ok' | 'down'。"""
    from app.api.routers.system import _probe_db

    result = asyncio.run(_probe_db())
    assert result in {"ok", "down"}


def test_probe_redis_returns_string() -> None:
    """_probe_redis 返回值必须是 'ok' | 'down'。"""
    from app.api.routers.system import _probe_redis

    result = asyncio.run(_probe_redis())
    assert result in {"ok", "down"}


def test_probe_llm_returns_string() -> None:
    """_probe_llm 返回值必须是 'ok' | 'degraded' | 'down'。"""
    from app.api.routers.system import _probe_llm

    result = asyncio.run(_probe_llm())
    assert result in {"ok", "degraded", "down"}
