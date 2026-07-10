"""System router（基础设施探针）。

PR-1（SPEC-S1PR1-fastapi-boot）：
- ``GET /healthz``：四段探针（db / redis / minio / llm），返回 OK / DEGRADED / DOWN
- 探针用 ``asyncio.gather`` 并发，单探针 2s timeout
- 任一关键依赖（db / redis）down → HTTP 503；llm / minio degraded → HTTP 200（降级不阻塞）

真源：本文件 db / redis / minio 探针复用 ``app.core.startup`` 的实现（单一真源）；
     LLM 探针仅在运行时使用，留在本文件。
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.conf.app_config import app_config
from app.core.log import logger
from app.core.startup import probe_postgres, probe_redis, probe_minio

# ──────────────────────────────────────────────────────────────────────────────
# §一 路由
# ──────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="", tags=["system"])

# 探针返回类型字面量
ProbeResult = Literal["ok", "down", "degraded"]

# /healthz 单探针 timeout（秒）—— 比启动期略短
_HEALTHZ_PROBE_TIMEOUT_SEC = 2.0


# ──────────────────────────────────────────────────────────────────────────────
# §二 探针实现：db / redis 委托给 app.core.startup
# ──────────────────────────────────────────────────────────────────────────────
async def _probe_db() -> ProbeResult:
    """PostgreSQL 探针：复用 startup 的实现。失败 → 'down'。"""
    try:
        return await asyncio.wait_for(probe_postgres(), timeout=_HEALTHZ_PROBE_TIMEOUT_SEC)
    except TimeoutError:
        logger.warning("healthz_db_timeout", timeout_sec=_HEALTHZ_PROBE_TIMEOUT_SEC)
        return "down"


async def _probe_redis() -> ProbeResult:
    """Redis 探针：复用 startup 的实现。失败 → 'down'。"""
    try:
        return await asyncio.wait_for(probe_redis(), timeout=_HEALTHZ_PROBE_TIMEOUT_SEC)
    except TimeoutError:
        logger.warning("healthz_redis_timeout", timeout_sec=_HEALTHZ_PROBE_TIMEOUT_SEC)
        return "down"


async def _probe_minio() -> ProbeResult:
    """MinIO 探针：复用 startup 的实现。失败 → 'degraded'（不阻塞 /healthz 200）。"""
    try:
        return await asyncio.wait_for(probe_minio(), timeout=_HEALTHZ_PROBE_TIMEOUT_SEC)
    except TimeoutError:
        logger.warning("healthz_minio_timeout", timeout_sec=_HEALTHZ_PROBE_TIMEOUT_SEC)
        return "degraded"


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


# ──────────────────────────────────────────────────────────────────────────────
# §三 /healthz 端点
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/healthz",
    include_in_schema=False,  # 不污染 OpenAPI 业务契约（仅内部 liveness）
    summary="Liveness + 四段探针（db / redis / minio / llm）",
)
async def healthz() -> JSONResponse:
    """并发四段探针，返回 ``{status, checks}`` 响应体。

    - 全部 ok → ``status=ok`` + HTTP 200
    - 仅 llm / minio degraded → ``status=degraded`` + HTTP 200
    - 任一 db/redis down → ``status=down`` + HTTP 503
    - minio degraded 不影响 HTTP 状态码（storage 可降级）
    """
    db_res, redis_res, minio_res, llm_res = await asyncio.gather(
        _probe_db(),
        _probe_redis(),
        _probe_minio(),
        _probe_llm(),
    )
    checks: dict[str, str] = {
        "db": db_res,
        "redis": redis_res,
        "minio": minio_res,
        "llm": llm_res,
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

    body: dict[str, object] = {
        "status": status,
        "checks": checks,
    }
    return JSONResponse(status_code=http_code, content=body)


__all__ = ["router"]
