"""Integration smoke test — FastAPI app boots + middleware order + trace headers.

PR-1 (SPEC-S1PR1-fastapi-boot)：
- AC-1: /healthz 返回 200
- AC-2: 中间件挂载顺序正确（TraceContext 最外 → Exception → RateLimit）
- AC-3: trace headers 注入

实现真源：``backend/app/main.py``（PR-1 新建）。
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ──────────────────────────────────────────────────────────────────────────────
# §一 关键中间件类（用于检查挂载顺序）
# ──────────────────────────────────────────────────────────────────────────────
from app.api.middleware.exception_handler import ExceptionHandlerMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.trace import TraceContextMiddleware


@pytest.fixture(autouse=True)
def _stub_healthz_probes() -> Iterator[None]:
    """smoke：/healthz 调用会被多种用例复用，统一将三段探针桩成 ok。

    真正探针契约由 ``tests/integration/test_healthz_pings.py`` 覆盖。
    """
    with (
        patch("app.api.routers.system._probe_db", return_value="ok"),
        patch("app.api.routers.system._probe_redis", return_value="ok"),
        patch("app.api.routers.system._probe_llm", return_value="ok"),
    ):
        yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    """启动 FastAPI app + lifespan。"""
    from app.main import app

    with TestClient(app) as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# §二 AC-1: /healthz 真 boot + 200
# ──────────────────────────────────────────────────────────────────────────────
def test_healthz_returns_200(client: TestClient) -> None:
    """AC-1: GET /healthz → HTTP 200 + JSON 含 status / checks。"""
    response = client.get("/healthz")
    assert response.status_code == 200, (
        f"/healthz 期望 200，实际 {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "status" in body
    assert body["status"] in {"ok", "degraded"}
    assert "checks" in body
    assert set(body["checks"].keys()) == {"db", "redis", "llm"}


def test_app_title_is_selfwell(client: TestClient) -> None:
    """main.py 中 FastAPI app 标题必须为 'Selfwell Agent Backend'。"""
    from app.main import app

    assert app.title == "Selfwell Agent Backend"


# ──────────────────────────────────────────────────────────────────────────────
# §三 AC-2: 中间件挂载顺序
# ──────────────────────────────────────────────────────────────────────────────
def test_three_middlewares_mounted() -> None:
    """3 个核心中间件都已挂载（TraceContext / Exception / RateLimit）。"""
    from app.main import app

    middleware_classes = {mw.cls for mw in app.user_middleware}
    assert TraceContextMiddleware in middleware_classes
    assert ExceptionHandlerMiddleware in middleware_classes
    assert RateLimitMiddleware in middleware_classes


def test_middleware_order_outer_to_inner() -> None:
    """中间件顺序：TraceContext(最外) → Exception → RateLimit(最内)。

    FastAPI add_middleware 是 LIFO（后 add = 外层）。
    因此 user_middleware 列表索引顺序应为：
    index 0 = 最后 add = TraceContext (最外)
    index 1 = 中间 add = Exception
    index 2 = 最早 add = RateLimit (最内)
    """
    from app.main import app

    classes_in_order = [mw.cls for mw in app.user_middleware]
    assert TraceContextMiddleware in classes_in_order
    assert ExceptionHandlerMiddleware in classes_in_order
    assert RateLimitMiddleware in classes_in_order
    # 顺序断言：TraceContext 必须比 Exception 晚 add（即在 list 里更靠前）
    idx_trace = classes_in_order.index(TraceContextMiddleware)
    idx_exc = classes_in_order.index(ExceptionHandlerMiddleware)
    idx_rl = classes_in_order.index(RateLimitMiddleware)
    assert idx_trace < idx_exc < idx_rl, (
        f"中间件顺序错误（应为 TraceContext→Exception→RateLimit，"
        f"实际 add 顺序为 {classes_in_order}）"
    )


# ──────────────────────────────────────────────────────────────────────────────
# §四 AC-3: trace headers 注入
# ──────────────────────────────────────────────────────────────────────────────
def test_trace_headers_injected(client: TestClient) -> None:
    """无入站 trace 头时，响应必须注入 X-Trace-Id / X-Request-ID / traceparent。"""
    response = client.get("/healthz")
    assert response.status_code == 200

    # X-Trace-Id 必须是 32 字符 hex
    trace_id = response.headers.get("X-Trace-Id")
    assert trace_id is not None
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id), f"X-Trace-Id 格式错误：{trace_id}"

    # X-Request-ID 必须存在
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None

    # traceparent 形如 00-{32hex}-{16hex}-01
    traceparent = response.headers.get("traceparent")
    assert traceparent is not None
    assert re.fullmatch(r"00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}", traceparent), (
        f"traceparent 格式错误：{traceparent}"
    )


def test_trace_headers_propagate_inbound(client: TestClient) -> None:
    """入站带 X-Trace-Id 时，响应必须回传相同值（透传）。"""
    inbound_trace = "0" * 32  # 32 hex zeros
    response = client.get("/healthz", headers={"X-Trace-Id": inbound_trace})
    assert response.headers.get("X-Trace-Id") == inbound_trace


# ──────────────────────────────────────────────────────────────────────────────
# §五 OpenAPI 暴露
# ──────────────────────────────────────────────────────────────────────────────
def test_docs_endpoint_exposed(client: TestClient) -> None:
    """FastAPI /docs 端点可访问（OpenAPI Swagger UI）。"""
    response = client.get("/docs")
    assert response.status_code == 200
