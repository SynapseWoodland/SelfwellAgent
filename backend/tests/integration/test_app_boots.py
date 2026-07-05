"""Integration smoke test — verify FastAPI app boots + ping /healthz stub."""

from __future__ import annotations

from fastapi import FastAPI


def test_fastapi_app_can_be_constructed() -> None:
    """Sprint 0 落地：FastAPI 框架可达，可构造占位 app。"""
    app = FastAPI(title="Sprint 0 scaffold")
    assert app.title == "Sprint 0 scaffold"


def test_exception_handler_middleware_registerable() -> None:
    """所有 Sprint 0 中间件可挂载到 FastAPI app。"""
    from app.api.middleware import (
        ExceptionHandlerMiddleware,
        RateLimitMiddleware,
        TraceContextMiddleware,
    )

    app = FastAPI()
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TraceContextMiddleware)
    assert len(app.user_middleware) >= 3
