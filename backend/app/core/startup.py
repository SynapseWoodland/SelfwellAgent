"""启动期探针 + 配置摘要日志（Sprint 1 PR-1 扩展）。

真源：
- ``backend/app/main.py`` lifespan 启动期调用本模块
- ``backend/app/api/routers/system.py`` ``/healthz`` 也复用本模块的探针实现

约定：
1. 探针 **不抛异常** —— 成功 INFO，失败 ERROR（让 uvicorn 仍能起来，``/healthz`` 暴露故障）
2. 启动期 **必须** 打印：app_env / log_level / 各段 is_configured / 探针结果
3. 探针 timeout 短（3s）—— 启动期不能卡太久
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Literal, cast

from app.conf.app_config import app_config
from app.core.log import logger

# ─────────────────────────────────────────────────────────────────────────────
# §一 类型 / 常量
# ─────────────────────────────────────────────────────────────────────────────
ProbeResult = Literal["ok", "down", "degraded"]

# 启动期探针 timeout（秒）—— 比 /healthz 略宽，给首次 DNS / TCP 握手留时间
_STARTUP_PROBE_TIMEOUT_SEC = 3.0


# ─────────────────────────────────────────────────────────────────────────────
# §二 探针实现（无副作用 + 不抛异常）
# ─────────────────────────────────────────────────────────────────────────────
async def probe_postgres() -> ProbeResult:
    """PostgreSQL 探针：执行 SELECT 1。失败 → 'down'。

    实现：复用 ``app.db.session.get_engine()`` 的懒加载 engine。
    """
    try:
        from sqlalchemy import text

        from app.db.session import get_engine

        engine = get_engine()

        async def _do_probe() -> ProbeResult:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info(
                "startup_db_ok",
                host=app_config.postgres.host,
                port=app_config.postgres.port,
                db=app_config.postgres.db,
            )
            return "ok"

        return await asyncio.wait_for(_do_probe(), timeout=_STARTUP_PROBE_TIMEOUT_SEC)
    except TimeoutError:
        logger.error(
            "startup_db_timeout",
            timeout_sec=_STARTUP_PROBE_TIMEOUT_SEC,
            host=app_config.postgres.host,
            port=app_config.postgres.port,
            db=app_config.postgres.db,
        )
        return "down"
    except Exception as exc:
        logger.error(
            "startup_db_probe_failed",
            host=app_config.postgres.host,
            port=app_config.postgres.port,
            db=app_config.postgres.db,
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        return "down"


async def probe_redis() -> ProbeResult:
    """Redis 探针：PING。失败 → 'down'。"""
    try:
        from redis.asyncio import Redis

        redis_cfg = app_config.redis
        url = redis_cfg.url or f"redis://{redis_cfg.host}:{redis_cfg.port}/{redis_cfg.db}"
        password = redis_cfg.password or None
        client: Redis = Redis.from_url(
            url,
            password=password,
            socket_timeout=_STARTUP_PROBE_TIMEOUT_SEC,
        )

        async def _do_probe() -> ProbeResult:
            await cast("Awaitable[bool]", client.ping())
            logger.info(
                "startup_redis_ok",
                host=app_config.redis.host,
                port=app_config.redis.port,
            )
            return "ok"

        try:
            return await asyncio.wait_for(_do_probe(), timeout=_STARTUP_PROBE_TIMEOUT_SEC)
        finally:
            await client.aclose()
    except TimeoutError:
        logger.error(
            "startup_redis_timeout",
            timeout_sec=_STARTUP_PROBE_TIMEOUT_SEC,
            host=app_config.redis.host,
            port=app_config.redis.port,
        )
        return "down"
    except Exception as exc:
        logger.error(
            "startup_redis_probe_failed",
            host=app_config.redis.host,
            port=app_config.redis.port,
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        return "down"


async def probe_minio() -> ProbeResult:
    """MinIO 探针：HTTP GET /minio/health/live。失败 → 'degraded'（不影响主流程 critical 决策）。

    失败不阻塞启动（业务读图走 fallback）；只打日志提示。

    注意：
    - 不依赖 bucket 是否存在（避免开发态 404 误判）
    - 不走 Caddy 反代路径（开发态 Caddy 可能没起），直接探 MinIO S3 API 端口
    """
    minio_cfg = app_config.storage.minio
    if not minio_cfg.endpoint or not minio_cfg.root_password:
        logger.info("startup_minio_skipped", reason="endpoint or password not configured")
        return "degraded"
    try:
        import httpx

        scheme = "https" if minio_cfg.secure else "http"
        health_url = f"{scheme}://{minio_cfg.endpoint}/minio/health/live"

        async def _do_probe() -> ProbeResult:
            async with httpx.AsyncClient(timeout=_STARTUP_PROBE_TIMEOUT_SEC) as client_http:
                resp = await client_http.get(health_url)
                if resp.status_code == 200:
                    logger.info("startup_minio_ok", endpoint=minio_cfg.endpoint)
                    return "ok"
                logger.warning(
                    "startup_minio_health_check_failed",
                    endpoint=minio_cfg.endpoint,
                    status_code=resp.status_code,
                )
                return "degraded"

        return await asyncio.wait_for(_do_probe(), timeout=_STARTUP_PROBE_TIMEOUT_SEC)
    except TimeoutError:
        logger.warning(
            "startup_minio_timeout",
            timeout_sec=_STARTUP_PROBE_TIMEOUT_SEC,
            endpoint=minio_cfg.endpoint,
        )
        return "degraded"
    except Exception as exc:
        logger.warning(
            "startup_minio_probe_failed",
            endpoint=minio_cfg.endpoint,
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        return "degraded"


# ─────────────────────────────────────────────────────────────────────────────
# §三 启动期：配置摘要 + 三段探针并发执行
# ─────────────────────────────────────────────────────────────────────────────
async def run_startup_probes() -> dict[str, ProbeResult]:
    """启动期入口：先打配置摘要，再并发三段探针。

    Returns:
        ``{"db": ..., "redis": ..., "minio": ...}`` —— 供 lifespan 日志或 /healthz 复用。

    注意：本函数**不抛异常**，所有失败都已转成 ERROR 日志。

    """
    # 1. 启动摘要（每段是否配齐 + 关键 secret 的脱敏长度）
    logger.info(
        "startup_config_summary",
        app_env=app_config.app_env.value,
        log_level=app_config.log_level,
        backend_port=app_config.backend_port,
        postgres_configured=app_config.is_postgres_configured,
        postgres_host=app_config.postgres.host,
        postgres_port=app_config.postgres.port,
        postgres_db=app_config.postgres.db,
        redis_configured=app_config.is_redis_configured,
        redis_host=app_config.redis.host,
        redis_port=app_config.redis.port,
        llm_configured=app_config.is_llm_configured,
        wechat_configured=app_config.is_wechat_configured,
        wechat_appid_len=len(app_config.wechat.mp_appid),
        jwt_configured=app_config.is_jwt_configured,
        jwt_secret_len=len(app_config.jwt.secret_key),
        storage_configured=app_config.is_storage_configured,
        minio_endpoint=app_config.storage.minio.endpoint or "",
    )

    # 2. 三段探针并发（任一失败不阻塞其他 + 不阻塞启动）
    db_res, redis_res, minio_res = await asyncio.gather(
        probe_postgres(),
        probe_redis(),
        probe_minio(),
        return_exceptions=False,  # 探针内部已吞异常
    )

    # 3. 探针结果日志
    results: dict[str, ProbeResult] = {
        "db": db_res,
        "redis": redis_res,
        "minio": minio_res,
    }
    if db_res == "ok" and redis_res == "ok" and minio_res == "ok":
        logger.info("startup_probes_all_ok", **results)
    # 至少一个 down / degraded —— 显式打 ERROR 让告警捕获
    elif db_res == "down" or redis_res == "down":
        logger.error("startup_probes_critical_down", **results)
    else:
        logger.warning("startup_probes_degraded", **results)
    return results


__all__ = [
    "ProbeResult",
    "probe_minio",
    "probe_postgres",
    "probe_redis",
    "run_startup_probes",
]
