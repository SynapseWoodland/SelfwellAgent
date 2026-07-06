"""System router（基础设施探针）。

PR-1（SPEC-S1PR1-fastapi-boot）：
- ``GET /healthz``：三段探针（db / redis / llm），返回 OK / DEGRADED / DOWN
- 探针用 ``asyncio.gather`` 并发，单探针 2s timeout
- 任一关键依赖（db / redis）down → HTTP 503；仅 LLM down → HTTP 200（degraded）

不依赖 LLM 客户端具体实现（PR-1 不接 LLM 调用），仅 HTTP HEAD 检查 base_url。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Awaitable, Literal, cast

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.conf.app_config import app_config
from app.core.log import logger

if TYPE_CHECKING:
    pass

# ──────────────────────────────────────────────────────────────────────────────
# §一 路由
# ──────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="", tags=["system"])

# 探针返回类型字面量
ProbeResult = Literal["ok", "down", "degraded"]

# 单探针 timeout（秒）
_PROBE_TIMEOUT_SEC = 2.0


# ──────────────────────────────────────────────────────────────────────────────
# §二 探针实现（单测可 patch）
# ──────────────────────────────────────────────────────────────────────────────
async def _probe_db() -> ProbeResult:
    """PostgreSQL 探针：执行 SELECT 1。失败 → 'down'。"""
    try:
        from app.db.session import get_engine

        engine = get_engine()

        async def _do_probe() -> ProbeResult:
            async with engine.connect() as conn:
                from sqlalchemy import text

                await conn.execute(text("SELECT 1"))
            return "ok"

        return await asyncio.wait_for(_do_probe(), timeout=_PROBE_TIMEOUT_SEC)
    except TimeoutError:
        logger.warning("healthz_db_timeout", timeout_sec=_PROBE_TIMEOUT_SEC)
        return "down"
    except Exception:
        logger.exception("healthz_db_probe_failed")
        return "down"


async def _probe_redis() -> ProbeResult:
    """Redis 探针：PING。失败 → 'down'。

    本 PR 用 ``redis.asyncio`` 按 ``app_config.redis`` 拼 URL；首次调用时懒初始化 client。
    """
    try:
        from redis.asyncio import Redis

        redis_cfg = app_config.redis
        url = redis_cfg.url or f"redis://{redis_cfg.host}:{redis_cfg.port}/{redis_cfg.db}"
        password = redis_cfg.password or None
        client: Redis = Redis.from_url(
            url,
            password=password,
            socket_timeout=_PROBE_TIMEOUT_SEC,
        )

        async def _do_probe() -> ProbeResult:
            await cast("Awaitable[bool]", client.ping())
            return "ok"

        try:
            return await asyncio.wait_for(_do_probe(), timeout=_PROBE_TIMEOUT_SEC)
        finally:
            await client.aclose()
    except TimeoutError:
        logger.warning("healthz_redis_timeout", timeout_sec=_PROBE_TIMEOUT_SEC)
        return "down"
    except Exception:
        logger.exception("healthz_redis_probe_failed")
        return "down"


async def _probe_llm() -> ProbeResult:
    """LLM 探针：HTTP HEAD 任一 LLM provider 的 base_url；全部失败 → 'degraded'。

    本探针**不发起实际 LLM 调用**（PR-1 不接 LLM client）；仅检查 base_url 是否可达。
    不可达时 LLM 服务为降级状态（不影响主流程业务 HTTP 200）。
    """
    try:
        import httpx

        urls: list[str] = []
        if app_config.llm.anthropic.base_url:
            urls.append(app_config.llm.anthropic.base_url)
        if app_config.llm.openai.base_url:
            urls.append(app_config.llm.openai.base_url)
        # 没有配 base_url → 当作 ok（PR-1 不强制要求 LLM）
        if not urls:
            return "ok"

        async def _do_probe() -> ProbeResult:
            async with httpx.AsyncClient(timeout=_PROBE_TIMEOUT_SEC) as client_http:
                for url in urls:
                    try:
                        resp = await client_http.head(url)
                        if resp.status_code < 500:
                            return "ok"
                    except Exception:
                        logger.debug("healthz_llm_url_probe_skip", url=url)
                        continue
            return "degraded"

        return await asyncio.wait_for(_do_probe(), timeout=_PROBE_TIMEOUT_SEC * 1.5)
    except TimeoutError:
        logger.warning("healthz_llm_timeout", timeout_sec=_PROBE_TIMEOUT_SEC * 1.5)
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
    summary="Liveness + 三段探针（db / redis / llm）",
)
async def healthz() -> JSONResponse:
    """并发三段探针，返回 ``{status, checks}`` 响应体。

    - 全部 ok → ``status=ok`` + HTTP 200
    - 仅 llm degraded → ``status=degraded`` + HTTP 200
    - 任一 db/redis down → ``status=down`` + HTTP 503
    """
    db_res, redis_res, llm_res = await asyncio.gather(
        _probe_db(),
        _probe_redis(),
        _probe_llm(),
    )
    checks: dict[str, str] = {
        "db": db_res,
        "redis": redis_res,
        "llm": llm_res,
    }

    # 决策树
    if db_res == "down" or redis_res == "down":
        status: Literal["ok", "degraded", "down"] = "down"
        http_code = 503
    elif llm_res in {"degraded", "down"}:
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
