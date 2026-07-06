"""Selfwell Backend FastAPI 入口（Sprint 1 PR-1）。

PR-1（SPEC-S1PR1-fastapi-boot）目标：
1. 后端可 boot（uvicorn backend.app.main:app）
2. 暴露 ``GET /healthz`` + Swagger UI（``/docs``）
3. 挂载 3 个中间件（TraceContext → Exception → RateLimit）
4. lifespan 启动期调 ``setup_logging()``，收尾期释放资源

注意：
- 中间件 add 顺序是 LIFO（后 add = 外层）。要实现"TraceContext 最外 → Exception →
  RateLimit 最内"，应 **先 add RateLimit，再 add Exception，最后 add TraceContext**。
- 本文件**不**引入任何新依赖；所有 import 均已在 pyproject.toml 声明。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware.exception_handler import ExceptionHandlerMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.trace import TraceContextMiddleware
from app.api.routers.system import router as system_router
from app.conf.app_config import app_config
from app.core.log import setup_logging


# ──────────────────────────────────────────────────────────────────────────────
# §一 lifespan：启动期初始化日志 + 资源，shutdown 收尾
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan：启动期 setup_logging；shutdown 释放 DB engine。"""
    # 启动期：loguru 工厂初始化（幂等）
    setup_logging(level=app_config.log_level)

    # DB engine 懒加载（在首次 get_engine() 时初始化）；此处不显式创建。
    # 探针在 /healthz 触发时会拉起；本 lifespan 不预热，避免 import 时 DSN 解析失败。
    yield

    # 收尾期：释放 DB engine 连接池
    try:
        from app.db.session import dispose_engine

        await dispose_engine()
    except Exception:
        # dispose 失败不影响 uvicorn 正常退出；记录但不 raise
        from app.core.log import logger

        logger.exception("lifespan_shutdown_dispose_engine_failed")


# ──────────────────────────────────────────────────────────────────────────────
# §二 FastAPI 实例
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Selfwell Agent Backend",
    version="0.1.0",
    description="Selfwell AI Health Companion Backend（Sprint 1 PR-1 入口）",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────────────────────────────────────
# §三 中间件挂载（顺序：先 RateLimit，再 Exception，最后 TraceContext = 最外）
# ──────────────────────────────────────────────────────────────────────────────
# FastAPI add_middleware 是 LIFO；最后 add 的在请求处理时最外层
app.add_middleware(RateLimitMiddleware)  # 最早 add → 最内（最靠近业务 handler）
app.add_middleware(ExceptionHandlerMiddleware)  # 第二 add → 中
app.add_middleware(TraceContextMiddleware)  # 最后 add → 最外（第一个接收请求）


# ──────────────────────────────────────────────────────────────────────────────
# §四 路由注册（PR-1 仅 system router）
# ──────────────────────────────────────────────────────────────────────────────
app.include_router(system_router)


__all__ = ["app", "lifespan"]
