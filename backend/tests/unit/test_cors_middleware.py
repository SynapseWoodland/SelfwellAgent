"""Unit test — CORS 中间件（ADR-0018）。

真源：``docs/adr/0018-cors-policy.md`` §3.5 测试覆盖矩阵。

测试矩阵（5 条）：
1. ``test_cors_dev_wildcard_origin_allowed``
   - ``APP_ENV=dev`` + ``Origin: http://evil.com`` → 200 + CORS headers
2. ``test_cors_prod_white_listed_origin_allowed``
   - ``APP_ENV=prod`` + ``Origin: https://app.selfwell.cn`` → 200
3. ``test_cors_prod_unlisted_origin_forbidden``
   - ``APP_ENV=prod`` + ``Origin: https://evil.com`` → 非白名单不返回 Allow-Origin
4. ``test_cors_prod_empty_origins_raises_at_startup``
   - ``APP_ENV=prod`` + ``CORS_ORIGINS=""`` → ValueError (fail-fast)
5. ``test_cors_sse_options_preflight``
   - SSE 端点 OPTIONS 预检 → 200 + Access-Control-Allow-Origin

设计说明：
- ``app_config.cors`` 是模块级单例；测试用 ``monkeypatch.setenv`` 强制 reload
  ``app.conf.app_config`` 重新计算，确保 ``from_env`` 看到正确 env。
- 测试用自定义 FastAPI 实例（与 main.py 同样的中间件栈顺序），避免污染主 app。
"""

from __future__ import annotations

import importlib
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── helpers ──────────────────────────────────────────────────────────────────
def _build_test_app_with_cors(cors_cfg) -> FastAPI:
    """构造与生产 main.py 一致中间件栈 + CORS 配置的 FastAPI 实例（仅测试用）。

    中间件挂载顺序严格按 ADR-0018 §3.4：LIFO：RateLimit → Exception →
    TraceContext → CORSMiddleware（最内）。
    """
    from contextlib import asynccontextmanager

    from starlette.middleware.cors import CORSMiddleware

    from app.api.middleware.exception_handler import ExceptionHandlerMiddleware
    from app.api.middleware.rate_limit import RateLimitMiddleware
    from app.api.middleware.trace import TraceContextMiddleware

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    test_app = FastAPI(title="CORS-test", lifespan=_noop_lifespan)

    @test_app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @test_app.get("/api/v1/diagnosis/stream")
    async def sse_stream():
        return {"status": "sse-stub"}

    # 与 main.py 完全一致的中间件挂载顺序（LIFO）
    test_app.add_middleware(RateLimitMiddleware)
    test_app.add_middleware(ExceptionHandlerMiddleware)
    test_app.add_middleware(TraceContextMiddleware)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_cfg.allowed_origins,
        allow_credentials=cors_cfg.allow_credentials,
        allow_methods=cors_cfg.allow_methods,
        allow_headers=cors_cfg.allow_headers,
        expose_headers=cors_cfg.expose_headers,
        max_age=cors_cfg.max_age_seconds,
    )
    return test_app


def _reload_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    """强制 reload ``app.conf.app_config`` 让 ``app_config.cors`` 重新按当前 env 计算。"""
    # 注意：必须从 sys.modules 取模块 —— ``import X as Y`` 在某些场景下
    # 可能绑定到 ``__init__.py`` re-export 的同名属性（此处正好是 AppConfig 实例）。
    cfg_mod = sys.modules["app.conf.app_config"]
    importlib.reload(cfg_mod)
    if "app.conf" in sys.modules:
        importlib.reload(sys.modules["app.conf"])


@pytest.fixture
def dev_cors(monkeypatch: pytest.MonkeyPatch):
    """fixture：注入 ``APP_ENV=dev`` + 空 ``CORS_ORIGINS`` 并 reload app_config。"""
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("CORS_ORIGINS", "")
    _reload_cors(monkeypatch)
    from app.conf.app_config import app_config

    assert app_config.cors.allowed_origins == ["*"]
    return _build_test_app_with_cors(app_config.cors)


@pytest.fixture
def prod_cors_allowed(monkeypatch: pytest.MonkeyPatch):
    """fixture：注入 ``APP_ENV=prod`` + 白名单 1 个 origin 并 reload。"""
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv(
        "CORS_ORIGINS", "https://app.selfwell.cn,https://admin.selfwell.cn"
    )
    _reload_cors(monkeypatch)
    from app.conf.app_config import app_config

    assert app_config.cors.allowed_origins == [
        "https://app.selfwell.cn",
        "https://admin.selfwell.cn",
    ]
    assert app_config.cors.max_age_seconds == 600
    return _build_test_app_with_cors(app_config.cors)


# ── 1. dev wildcard 跨域允许 ────────────────────────────────────────────────
def test_cors_dev_wildcard_origin_allowed(dev_cors: FastAPI) -> None:
    """AC-CORS-1: dev 模式 + 任意 origin → CORS 头返回，业务 200。"""
    with TestClient(dev_cors) as client:
        resp = client.get("/healthz", headers={"Origin": "http://evil.com"})

    assert resp.status_code == 200
    allow_origin = resp.headers.get("access-control-allow-origin")
    # starlette 在 allow_origins=["*"] + allow_credentials=False 时回显请求 origin
    assert allow_origin in {"*", "http://evil.com"}, (
        f"dev wildcard 应回显 origin 或 *，got: {allow_origin!r}"
    )


# ── 2. prod 白名单允许 ──────────────────────────────────────────────────────
def test_cors_prod_white_listed_origin_allowed(
    prod_cors_allowed: FastAPI,
) -> None:
    """AC-CORS-2: prod 模式 + 白名单内 origin → 200 + Allow-Origin 回显。"""
    with TestClient(prod_cors_allowed) as client:
        resp = client.get(
            "/healthz", headers={"Origin": "https://app.selfwell.cn"}
        )

    assert resp.status_code == 200
    assert (
        resp.headers.get("access-control-allow-origin")
        == "https://app.selfwell.cn"
    )


# ── 3. prod 非白名单拒绝 ────────────────────────────────────────────────────
def test_cors_prod_unlisted_origin_forbidden(
    prod_cors_allowed: FastAPI,
) -> None:
    """AC-CORS-3: prod 模式 + 非白名单 origin → Allow-Origin 不回显该 origin。"""
    with TestClient(prod_cors_allowed) as client:
        resp = client.get(
            "/healthz", headers={"Origin": "https://evil.com"}
        )

    # starlette CORS：业务 handler 仍 200，但 Allow-Origin 不回显非白名单 origin
    assert resp.status_code == 200
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin != "https://evil.com", (
        f"prod 非白名单 origin 不应被回显，got: {allow_origin!r}"
    )


# ── 4. prod 空 CORS_ORIGINS 启动期 fail-fast ──────────────────────────────
def test_cors_prod_empty_origins_raises_at_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-CORS-4: APP_ENV=prod + CORS_ORIGINS='' → CORSConfig.from_env 抛 ValueError。

    真源：ADR-0018 §3.1 "prod 必须配置 CORS_ORIGINS，否则 fail-fast"。
    """
    from app.conf.app_config import CORSConfig

    with pytest.raises(ValueError, match="CORS_ORIGINS is empty"):
        CORSConfig.from_env(app_env="prod", cors_origins_env="")

    # dev 模式兜底：空值不报错
    cfg = CORSConfig.from_env(app_env="dev", cors_origins_env="")
    assert cfg.allowed_origins == ["*"]


def test_cors_prod_whitespace_only_origins_raises() -> None:
    """边界场景：仅含逗号/空格的 CORS_ORIGINS 视为空，prod 同样 fail-fast。"""
    from app.conf.app_config import CORSConfig

    with pytest.raises(ValueError, match="CORS_ORIGINS is empty"):
        CORSConfig.from_env(app_env="prod", cors_origins_env=" , , ")


# ── 5. SSE 端点 OPTIONS 预检 ────────────────────────────────────────────────
def test_cors_sse_options_preflight(dev_cors: FastAPI) -> None:
    """AC-CORS-5: SSE 端点 OPTIONS 预检 → 200 + Access-Control-Allow-Origin 回显。

    背景：浏览器跨域发 POST /api/v1/diagnosis/stream 前会先发 OPTIONS 预检；
    若 OPTIONS 被拒，SSE 流永远接不通。ADR-0018 §3.5 矩阵第 5 行覆盖此场景。
    """
    with TestClient(dev_cors) as client:
        resp = client.options(
            "/api/v1/diagnosis/stream",
            headers={
                "Origin": "https://app.selfwell.cn",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization, content-type",
            },
        )

    assert resp.status_code == 200, (
        f"SSE OPTIONS 预检应 200，got {resp.status_code}；CORS 中间件可能未生效"
    )
    allow_origin = resp.headers.get("access-control-allow-origin")
    allow_methods = resp.headers.get("access-control-allow-methods", "")
    assert allow_origin in {"*", "https://app.selfwell.cn"}, (
        f"dev 应回显 origin 或 *；got: {allow_origin!r}"
    )
    assert "POST" in allow_methods, (
        f"预检响应应声明 POST 允许；got methods: {allow_methods!r}"
    )
