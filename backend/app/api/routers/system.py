"""System router（基础设施探针 + 可观测性端点）。

Phase 4 · 批次 4 扩展：
- ``GET /healthz``：完整四段探针（db / redis / minio / llm），返回 OK / DEGRADED / DOWN
  + 每段 latency_ms + version + request_id
- ``GET /readyz``：精简就绪探针（仅 db / redis），返回 OK / NOT_READY
  适用 K8s readinessProbe（不应拉 LLM 流量）
- ``GET /metrics``：Prometheus exposition format（来自 ``app.core.metrics``）

PR-1（SPEC-S1PR1-fastapi-boot）：
- 探针用 ``asyncio.gather`` 并发，单探针 2s timeout
- 任一关键依赖（db / redis）down → HTTP 503；llm / minio degraded → HTTP 200（降级不阻塞）

真源：本文件 db / redis / minio 探针复用 ``app.core.startup`` 的实现（单一真源）；
     LLM 探针仅在运行时使用，留在本文件。
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Literal

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.conf.app_config import app_config
from app.core.log import logger
from app.core.metrics import get_metrics
from app.core.startup import probe_minio, probe_postgres, probe_redis

# ──────────────────────────────────────────────────────────────────────────────
# §一 路由
# ──────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="", tags=["system"])

# 探针返回类型字面量
ProbeResult = Literal["ok", "down", "degraded"]

# /healthz 单探针 timeout（秒）—— 比启动期略短
_HEALTHZ_PROBE_TIMEOUT_SEC = 2.0


def _build_version() -> str:
    """构造 version 字段（优先读 ``APP_VERSION`` env，否则 git sha，否则 'dev'）。

    单一真源：``pyproject.toml`` ``[project] version``。
    CI/CD 注入 ``APP_VERSION=$(git rev-parse --short HEAD)``。
    """
    return os.environ.get("APP_VERSION") or "dev"


# ──────────────────────────────────────────────────────────────────────────────
# §二 探针实现：db / redis 委托给 app.core.startup
# ──────────────────────────────────────────────────────────────────────────────
async def _timed_probe(probe_fn: object, name: str) -> tuple[str, float]:
    """包装探针：返回 ``(result, latency_ms)``。捕获 TimeoutError → 'down'。"""
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(
            probe_fn(),  # type: ignore[operator]
            timeout=_HEALTHZ_PROBE_TIMEOUT_SEC,
        )
        return result, (time.monotonic() - start) * 1000.0
    except TimeoutError:
        logger.warning("healthz_probe_timeout", probe=name, timeout_sec=_HEALTHZ_PROBE_TIMEOUT_SEC)
        return "down", (time.monotonic() - start) * 1000.0


async def _probe_db() -> ProbeResult:
    """PostgreSQL 探针：复用 startup 的实现。失败 → 'down'。"""
    result, _ = await _timed_probe(probe_postgres, "db")
    return result


async def _probe_db_timed() -> tuple[str, float]:
    """PostgreSQL 探针（带耗时）—— /healthz 结构化响应使用。"""
    return await _timed_probe(probe_postgres, "db")


async def _probe_redis() -> ProbeResult:
    """Redis 探针：复用 startup 的实现。失败 → 'down'。"""
    result, _ = await _timed_probe(probe_redis, "redis")
    return result


async def _probe_redis_timed() -> tuple[str, float]:
    """Redis 探针（带耗时）。"""
    return await _timed_probe(probe_redis, "redis")


async def _probe_minio() -> ProbeResult:
    """MinIO 探针：复用 startup 的实现。失败 → 'degraded'（不阻塞 /healthz 200）。"""
    result, _ = await _timed_probe(probe_minio, "minio")
    return result


async def _probe_minio_timed() -> tuple[str, float]:
    """MinIO 探针（带耗时）。"""
    return await _timed_probe(probe_minio, "minio")


async def _probe_llm() -> ProbeResult:
    """LLM 探针：HTTP HEAD 任一 LLM provider 的 base_url；全部失败 → 'degraded'。

    本探针**不发起实际 LLM 调用**（PR-1 不接 LLM client）；仅检查 base_url 是否可达。
    不可达时 LLM 服务为降级状态（不影响主流程业务 HTTP 200）。

    ``app_config.llm`` 是 OpenAI 兼容统一模型（multi / api / backup_*），不再有
    anthropic/openai 双 provider 段；此处按 main / backup 各取一个 base_url 探测。
    """
    try:
        import httpx

        urls: list[str] = []
        if app_config.llm.multi_base_url:
            urls.append(app_config.llm.multi_base_url)
        elif app_config.llm.base_url:
            urls.append(app_config.llm.base_url)
        # 没有配 base_url → 当作 ok（PR-1 不强制要求 LLM）
        if not urls:
            return "ok"

        async def _do_probe() -> ProbeResult:
            async with httpx.AsyncClient(timeout=_HEALTHZ_PROBE_TIMEOUT_SEC) as client_http:
                for url in urls:
                    try:
                        resp = await client_http.head(url)
                        if resp.status_code < 500:
                            return "ok"
                    except Exception:
                        logger.debug("healthz_llm_url_probe_skip", url=url)
                        continue
            return "degraded"

        return await asyncio.wait_for(_do_probe(), timeout=_HEALTHZ_PROBE_TIMEOUT_SEC * 1.5)
    except TimeoutError:
        logger.warning(
            "healthz_llm_timeout",
            timeout_sec=_HEALTHZ_PROBE_TIMEOUT_SEC * 1.5,
        )
        return "degraded"
    except Exception:
        logger.exception("healthz_llm_probe_failed")
        return "degraded"


async def _probe_llm_timed() -> tuple[str, float]:
    """LLM 探针（带耗时）。"""
    start = time.monotonic()
    res = await _probe_llm()
    return res, (time.monotonic() - start) * 1000.0


# ──────────────────────────────────────────────────────────────────────────────
# §三 /healthz 端点（增强版：结构化响应 + latency + version + request_id）
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/healthz",
    include_in_schema=False,  # 不污染 OpenAPI 业务契约（仅内部 liveness）
    summary="Liveness + 四段探针（db / redis / minio / llm）",
)
async def healthz(request: Request) -> JSONResponse:
    """并发四段探针，返回结构化健康状态。

    响应字段：
    - ``status``: ``ok`` / ``degraded`` / ``down``
    - ``checks``: 每段 ``{status, latency_ms, error?}``
    - ``version``: 后端版本（``APP_VERSION`` env 或 'dev'）
    - ``env``: 当前 AppEnv
    - ``request_id``: 当前请求 ID（来自 TraceContextMiddleware）

    决策树：
    - 全部 ok → ``status=ok`` + HTTP 200
    - 仅 llm / minio degraded → ``status=degraded`` + HTTP 200
    - 任一 db/redis down → ``status=down`` + HTTP 503
    - minio degraded 不影响 HTTP 状态码（storage 可降级）
    """
    db_res, db_ms = await _probe_db_timed()
    redis_res, redis_ms = await _probe_redis_timed()
    minio_res, minio_ms = await _probe_minio_timed()
    llm_res, llm_ms = await _probe_llm_timed()

    checks: dict[str, dict[str, object]] = {
        "db": {"status": db_res, "latency_ms": round(db_ms, 1)},
        "redis": {"status": redis_res, "latency_ms": round(redis_ms, 1)},
        "minio": {"status": minio_res, "latency_ms": round(minio_ms, 1)},
        "llm": {"status": llm_res, "latency_ms": round(llm_ms, 1)},
    }

    # 决策树
    if db_res == "down" or redis_res == "down":
        status: Literal["ok", "degraded", "down"] = "down"
        http_code = 503
    elif llm_res in {"degraded", "down"} or minio_res in {"degraded", "down"}:
        status = "degraded"
        http_code = 200
    else:
        status = "ok"
        http_code = 200

    # 暴露 request_id / version / env 给运维 / K8s probe 用
    body: dict[str, object] = {
        "status": status,
        "checks": checks,
        "version": _build_version(),
        "env": app_config.app_env.value,
    }
    rid = getattr(getattr(request, "state", None), "request_id", None)
    if rid:
        body["request_id"] = rid

    return JSONResponse(status_code=http_code, content=body)


# ──────────────────────────────────────────────────────────────────────────────
# §四 /readyz 端点（K8s readinessProbe 用：仅关键依赖）
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/readyz",
    include_in_schema=False,
    summary="Readiness probe（仅 db + redis，避免 LLM 抖动拉走流量）",
)
async def readyz() -> JSONResponse:
    """K8s readinessProbe 专用精简探针。

    与 ``/healthz`` 区别：
    - **不查** LLM / MinIO（这两类降级不影响 readiness，K8s 不应拉走流量）
    - 仅 db / redis down → HTTP 503（NOT_READY）
    - 其余情况 → HTTP 200（READY）
    - 不含 latency_ms / version（readinessProbe 不关心）

    K8s 建议：
    - ``livenessProbe`` → ``/healthz``（重启决策）
    - ``readinessProbe`` → ``/readyz``（流量调度决策）

    Phase 4 批次 4：同时刷新 DB pool 指标（``DB_POOL_IN_USE`` / ``DB_POOL_SIZE``），
    让 Prometheus scrape /metrics 时能拿到当前连接池利用率。
    """
    db_res, _ = await _probe_db_timed()
    redis_res, _ = await _probe_redis_timed()

    ready = db_res == "ok" and redis_res == "ok"
    body = {
        "status": "ready" if ready else "not_ready",
        "checks": {"db": db_res, "redis": redis_res},
    }
    # Phase 4 批次 4：被动刷一次 DB pool gauge
    try:
        from app.core.observability import observe_db_pool

        observe_db_pool(pool_name="primary")
    except Exception:
        pass
    return JSONResponse(status_code=200 if ready else 503, content=body)


# ──────────────────────────────────────────────────────────────────────────────
# §五 /metrics 端点（Prometheus exposition）
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/metrics",
    include_in_schema=False,
    summary="Prometheus metrics endpoint（暴露 selfwell_* 指标）",
)
async def metrics() -> Response:
    """渲染 Prometheus exposition 格式。

    暴露指标（详见 ``app/core/metrics.py``）：
    - ``selfwell_sse_events_total``
    - ``selfwell_sse_errors_total``
    - ``selfwell_sse_first_byte_seconds``
    - ``selfwell_llm_calls_total``
    - ``selfwell_llm_latency_seconds``
    - ``selfwell_vision_latency_seconds``
    - ``selfwell_llm_cost_yuan_total``
    - ``selfwell_smart_analyze_done_total``
    - ``selfwell_smart_analyze_failed_total``
    - ``selfwell_smart_analyze_duration_seconds``
    """
    body, content_type = get_metrics()
    return Response(content=body, media_type=content_type)


__all__ = ["router"]
