"""Integration test — /healthz four-segment probes (db / redis / minio / llm).

Phase 4 batch 4: structured response with latency_ms + status, plus minio probe.
"""
from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _patch_all(db="ok", redis="ok", minio="ok", llm="ok", ms=1.0):
    """Returns a context manager stack with all four probes patched."""
    return ExitStack().__enter__()


def _enter_patches(stack: ExitStack, db="ok", redis="ok", minio="ok", llm="ok", ms=1.0):
    stack.enter_context(patch("app.api.routers.system._probe_db_timed", return_value=(db, ms)))
    stack.enter_context(
        patch("app.api.routers.system._probe_redis_timed", return_value=(redis, ms))
    )
    stack.enter_context(
        patch("app.api.routers.system._probe_minio_timed", return_value=(minio, ms))
    )
    stack.enter_context(
        patch("app.api.routers.system._probe_llm_timed", return_value=(llm, ms))
    )


@pytest.fixture
def probes_ok() -> Iterator[None]:
    stack = _patch_all()
    _enter_patches(stack)
    try:
        yield
    finally:
        stack.close()


@pytest.fixture
def probes_llm_degraded() -> Iterator[None]:
    stack = _patch_all()
    _enter_patches(stack, llm="degraded")
    try:
        yield
    finally:
        stack.close()


@pytest.fixture
def probes_db_down() -> Iterator[None]:
    stack = _patch_all()
    _enter_patches(stack, db="down")
    try:
        yield
    finally:
        stack.close()


@pytest.fixture
def probes_redis_down() -> Iterator[None]:
    stack = _patch_all()
    _enter_patches(stack, redis="down")
    try:
        yield
    finally:
        stack.close()


@pytest.fixture
def probes_all_down() -> Iterator[None]:
    stack = _patch_all()
    _enter_patches(stack, db="down", redis="down", minio="down", llm="down")
    try:
        yield
    finally:
        stack.close()


def test_healthz_all_ok_returns_200(probes_ok) -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # Phase 4 batch 4: structured response with latency_ms per segment
    assert body["checks"]["db"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"
    assert body["checks"]["minio"]["status"] == "ok"
    assert body["checks"]["llm"]["status"] == "ok"
    assert "latency_ms" in body["checks"]["db"]
    assert "version" in body
    assert "env" in body


def test_healthz_llm_degraded_returns_200(probes_llm_degraded) -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["llm"]["status"] == "degraded"
    assert body["checks"]["db"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"


def test_healthz_db_down_returns_503(probes_db_down) -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "down"
    assert body["checks"]["db"]["status"] == "down"


def test_healthz_redis_down_returns_503(probes_redis_down) -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "down"
    assert body["checks"]["redis"]["status"] == "down"


def test_healthz_all_down_returns_503(probes_all_down) -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "down"


# ──────────────────────────────────────────────────────────────────────────────
# Section: probe functions themselves (raw value contracts)
# ──────────────────────────────────────────────────────────────────────────────
def test_probe_db_returns_string() -> None:
    """_probe_db returns one of 'ok' | 'down'."""
    from app.api.routers.system import _probe_db

    result = asyncio.run(_probe_db())
    assert result in {"ok", "down"}


def test_probe_redis_returns_string() -> None:
    from app.api.routers.system import _probe_redis

    result = asyncio.run(_probe_redis())
    assert result in {"ok", "down"}


def test_probe_llm_returns_string() -> None:
    from app.api.routers.system import _probe_llm

    result = asyncio.run(_probe_llm())
    assert result in {"ok", "degraded", "down"}