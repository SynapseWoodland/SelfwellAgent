"""可观测性埋点工具（Phase 4 · 批次 4）。

集中所有需要"零侵入"接入 metrics / trace_id 的 helper，避免散落在
``assistant_service`` / ``diagnosis_service`` 里导致遗漏。

设计原则：
1. **Failure-isolated**：任何埋点失败都不能影响主流程，所以全部 ``try/except`` 包住
   （即便 metrics 模块未加载、SSE 已经断流、DB pool 关闭了，也最多"少一次"打点）。
2. **Label contract 保留**：``is_mock`` / ``is_fallback`` 是已存在的 label 名
   （``docs/architecture/api.yaml`` + Golden Set 都引用了），一律兼容。
3. **不依赖 Prometheus 默认 registry**：全部走 ``app.core.metrics.METRICS_REGISTRY``，
   与现有 LLM/SSE 指标同源。

公开 API：
- :func:`observe_sse_event`  —— 给 SSE 发送方打点（per-event 计数 + 阶段耗时）
- :func:`observe_sse_disconnect` —— SSE 提前终止（client disconnect / generator 异常退出）
- :func:`observe_db_pool` —— DB 连接池利用率（建议在健康检查 / 慢查询告警时拉一次）
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


def _safe_metric(name: str):
    """延迟导入 metrics（避免循环引用 + 测试时可以 monkeypatch）。"""
    try:
        from app.core import metrics as _m

        return getattr(_m, name)
    except Exception:
        return None


def observe_sse_event(
    *,
    endpoint: str,
    event_name: str,
    duration_seconds: float | None = None,
    stage: str | None = None,
) -> None:
    """记录一次 SSE 事件发送。

    Args:
        endpoint: 路由名（例: ``"assistant.send_message_stream"`` / ``"diagnosis.job_stream"``）。
        event_name: 事件名（``start`` / ``progress`` / ``token_delta`` / ``end`` / ``error`` ...）。
        duration_seconds: 本帧从触发到 yield 的耗时（秒）。None 表示不记录阶段耗时。
        stage: 阶段名（用于 5 阶段 SSE 链路追踪；例 ``vision_analyze``、``generate_plan``）。

    失败时静默 —— SSE 流式响应不能因为打点失败而整条流都崩。

    """
    try:
        events_total = _safe_metric("SSE_EVENTS_TOTAL")
        if events_total is not None:
            events_total.labels(endpoint=endpoint, event_name=event_name).inc()
        if event_name == "error":
            err_total = _safe_metric("SSE_ERRORS_TOTAL")
            if err_total is not None:
                err_total.labels(endpoint=endpoint, error_code=event_name).inc()
        if duration_seconds is not None and stage:
            stage_h = _safe_metric("SSE_STAGE_DURATION_SECONDS")
            if stage_h is not None:
                stage_h.labels(endpoint=endpoint, stage=stage).observe(duration_seconds)
    except Exception:
        # 任何埋点失败都不影响主流程
        return


def observe_sse_disconnect(*, endpoint: str, reason: str) -> None:
    """记录一次 SSE 提前终止（client 断开 / generator 异常退出）。

    与 ``SSE_EVENTS_TOTAL`` 不同：``disconnect`` 是"没有收到 end 事件"也
    没有"event=error"，所以单独一个 counter 用来算 "disconnect rate"。
    """
    try:
        counter = _safe_metric("SSE_DISCONNECTED_TOTAL")
        if counter is not None:
            counter.labels(endpoint=endpoint, reason=reason).inc()
    except Exception:
        return


def observe_db_pool(*, pool_name: str = "default") -> None:
    """记录当前 DB pool 利用率（``in_use`` + ``size``）。

    调用方：在慢查询告警 / 健康检查 / 后台轮询里拉一次即可。
    不会抛错 —— pool 已被 dispose 时 ``checkedout()`` 抛 AttributeError 也只会被吞掉。
    """
    try:
        size_g = _safe_metric("DB_POOL_SIZE")
        in_use_g = _safe_metric("DB_POOL_IN_USE")
        if size_g is None or in_use_g is None:
            return
        from app.db.session import get_engine

        engine = get_engine()
        pool = engine.pool
        # QueuePool.checkedout() 返回当前借出的连接数
        size = getattr(pool, "size", lambda: 0)()
        checked_out = getattr(pool, "checkedout", lambda: 0)()
        size_g.labels(pool=pool_name).set(size)
        in_use_g.labels(pool=pool_name).set(checked_out)
    except Exception:
        return


@contextmanager
def track_sse_stage(endpoint: str, stage: str) -> Iterator[dict[str, Any]]:
    """上下文管理器：记录一段 SSE 阶段耗时（开始 → 结束）。

    Usage::

        with track_sse_stage("assistant.smart_analyze", "vision_analyze") as ctx:
            result = await call_vision_llm(...)
        # ctx["duration_seconds"] 自动填入
    """
    ctx: dict[str, Any] = {"duration_seconds": 0.0, "stage": stage}
    start = time.perf_counter()
    try:
        yield ctx
    finally:
        try:
            ctx["duration_seconds"] = time.perf_counter() - start
            observe_sse_event(
                endpoint=endpoint,
                event_name="stage",
                duration_seconds=ctx["duration_seconds"],
                stage=stage,
            )
        # observability 失败时不阻断主流程（且已经在 try/except 内）
        except Exception as exc:
            from app.core.log import logger

            logger.debug("track_sse_stage_observe_failed", exc_type=type(exc).__name__)
            return


__all__ = [
    "observe_db_pool",
    "observe_sse_disconnect",
    "observe_sse_event",
    "track_sse_stage",
]
