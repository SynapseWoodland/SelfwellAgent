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
from starlette.middleware.cors import CORSMiddleware

from app.api.middleware.exception_handler import ExceptionHandlerMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.trace import TraceContextMiddleware
from app.api.routers.assistant_v1 import assistant_router
from app.api.routers.auth import router as auth_router_legacy
from app.api.routers.auth_v1 import router as auth_v1_router
from app.api.routers.butler_v1 import butler_router
from app.api.routers.checkin_v1 import checkin_router
from app.api.routers.community_v1 import community_router
from app.api.routers.diagnosis_v1 import router as diagnosis_v1_router
from app.api.routers.feedback_v1 import feedback_router
from app.api.routers.plans_v1 import plans_router, videos_router
from app.api.routers.share_v1 import share_router
from app.api.routers.system import router as system_router
from app.api.routers.uploads_v1 import router as uploads_v1_router
from app.api.routers.users_v1 import router as users_v1_router
from app.api.routers.v2 import v2_router
from app.conf.app_config import app_config
from app.core.job_state import InMemoryJobStateStore
from app.core.log import logger, setup_logging


# ──────────────────────────────────────────────────────────────────────────────
# §一 lifespan：启动期初始化日志 + 配置摘要 + 三段探针，shutdown 收尾
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan。

    启动期：
    1. ``setup_logging()`` 初始化 loguru
    2. ``run_startup_probes()`` 并发探活 db / redis / minio + 打配置摘要
       任何探针失败都打 ERROR 日志（不 raise，让 uvicorn 继续启动）
    3. DB engine 仍走懒加载（首次 get_engine() 时初始化），避免 import 时 DSN 解析失败
    4. PR-A1：实例化 ``InMemoryJobStateStore`` 并挂到 ``app.state.job_state``，
       SSE 路由（PR-A2）从 ``request.app.state.job_state`` 取同一份

    shutdown：
    1. ``dispose_engine()`` 释放 DB 连接池
    2. PR-A1：关闭 ``app.state.job_state``（清空所有未消费 job —— 内存态，无持久化）
    """
    # 1. loguru 工厂初始化（幂等）
    setup_logging(level=app_config.log_level)

    # 2. Windows PowerShell stdout 中文/emoji 截断兜底
    import sys as _sys
    if _sys.platform == "win32":
        try:
            _sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass

    # 3. 启动期探活：配置摘要 + db / redis / minio 探针并发
    #    探针内部已吞所有异常 → 不会因外部服务挂掉而阻断 uvicorn 启动
    try:
        from app.core.startup import run_startup_probes

        await run_startup_probes()
    except Exception:
        # 兜底：startup 模块自身出错也要让进程起来
        logger.exception("lifespan_startup_probes_crashed")

    # 4. PR-A1：JobStateStore 初始化 + 挂载到 app.state
    #    单实例内存态；多 worker 部署需在 PR-A2+ 切到 Redis 适配
    job_state = InMemoryJobStateStore()
    app.state.job_state = job_state
    logger.info("lifespan_job_state_ready", ttl_seconds=job_state._ttl_seconds)

    yield

    # 收尾期：释放 DB engine 连接池
    try:
        from app.db.session import dispose_engine

        await dispose_engine()
    except Exception:
        # dispose 失败不影响 uvicorn 正常退出；记录但不 raise
        logger.exception("lifespan_shutdown_dispose_engine_failed")

    # PR-A1：关闭 JobStateStore —— 清空所有未消费 job
    try:
        job_state = getattr(app.state, "job_state", None)
        if job_state is not None:
            job_state.close_all()
    except Exception:
        logger.exception("lifespan_shutdown_job_state_failed")


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
# §三 中间件挂载（顺序 LIFO：最外 = 最后 add）
#   TraceContext → Exception → RateLimit → CORSMiddleware（最内，业务路由前把最后一关）
# ──────────────────────────────────────────────────────────────────────────────
# FastAPI add_middleware 是 LIFO；最后 add 的在请求处理时最外层
app.add_middleware(RateLimitMiddleware)  # 最早 add → 最内层
app.add_middleware(ExceptionHandlerMiddleware)  # 第二 add
app.add_middleware(TraceContextMiddleware)  # 第三 add
# ADR-0018：CORSMiddleware 放在 LIFO 最内层（业务路由前最后一道关）
# 让 trace / exception / rate_limit 先做；CORS 仅负责"跨域可不可被访问"的最终判定。
cors_cfg = app_config.cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_cfg.allowed_origins,
    allow_credentials=cors_cfg.allow_credentials,
    allow_methods=cors_cfg.allow_methods,
    allow_headers=cors_cfg.allow_headers,
    expose_headers=cors_cfg.expose_headers,
    max_age=cors_cfg.max_age_seconds,
)


# ──────────────────────────────────────────────────────────────────────────────
# §四 路由注册（PR-1 仅 system router）
# ──────────────────────────────────────────────────────────────────────────────
app.include_router(system_router)
app.include_router(auth_router_legacy)
app.include_router(auth_v1_router, prefix="/api/v1")
app.include_router(users_v1_router, prefix="/api/v1")
app.include_router(diagnosis_v1_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(videos_router, prefix="/api/v1")
app.include_router(checkin_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(community_router, prefix="/api/v1")
app.include_router(butler_router, prefix="/api/v1")
app.include_router(share_router, prefix="/api/v1")
app.include_router(uploads_v1_router, prefix="/api/v1")
# PR-2 V2 IA：9 接口 + 1 辅助 endpoint 挂在 /api/v1/v2/
app.include_router(v2_router, prefix="/api/v1")


__all__ = ["app", "lifespan"]
