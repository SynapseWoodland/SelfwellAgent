"""Prometheus metrics 模块（V4.1 Phase 3 Step 3.1 + V4.1.1 扩展指标）。

真源：
- ``docs/api/sse-events.md``（SSE 事件 schema）
- ``docs/plan/assistant-smart-analyze-vision-pipeline_4_feasibility-benchmarks.md``
  §1（sliding window log）+ §6（vision LLM 灰度 4 档 promote gate）+
  §9（AI 自审 severity 分级）
- ``assistant-smart-analyze-vision-pipeline_4_cursor-exec-plan.md``
  Step 1.6（ratelimit）+ Step 3.1（metrics）+ Step 3.7（text_llm.model 兜底）

约定：
1. 所有指标挂 ``namespace="selfwell"`` —— 避免与同机其它 service 指标冲突。
2. Counter 命名 ``<area>_<event>_total``；Histogram ``<area>_<latency>_seconds``。
3. Bucket 选择以 vision LLM 冷启动 5-15s + chat astream 实时为锚，
   主覆盖 [0.05, 0.5, 1, 5, 10, 30, 60]，长尾放到 120s。
4. ``vision_timeout_sec`` 默认 30.0 秒 —— 与
   ``assistant-smart-analyze-vision-pipeline_4_feasibility-benchmarks.md``
   §7 P0-3 推荐的 vision LLM 超时阈值对齐（rule-engine fallback 兜底）。
5. ``get_metrics()`` 渲染 ``text/plain; version=0.0.4`` Prometheus exposition format；
   由 ``main.py`` 挂在 ``GET /metrics`` 路由提供给 Prometheus server 拉取。

不在此处做的事：
- 不做 Sentry 上报（Sprint C 末尾可选接入，详见 Step 3.7）。
- 不做 Grafana Dashboard JSON 生成（属 deployment 范畴）。
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

# ─────────────────────────────────────────────────────────────────────────
# §一 Vision LLM 超时默认值（与行业对标 §7 / Step 1.2 对齐）
# ─────────────────────────────────────────────────────────────────────────
VISION_TIMEOUT_SEC: float = 30.0
"""vision LLM 调用 ``asyncio.wait_for`` 超时阈值（秒）。

依据 ``assistant-smart-analyze-vision-pipeline_4_feasibility-benchmarks.md``
§7 P0-3：vision 模型冷启动 5-15s 是常态，30s 是"用户感知可接受上限"。
超过则降级到 ``_rule_engine_fallback``（详见 ``diagnosis_service.py:540-557``）。
"""

# ─────────────────────────────────────────────────────────────────────────
# §二 指标 registry（独立命名空间，不污染全局默认 registry）
# ─────────────────────────────────────────────────────────────────────────
# 故意不复用 prometheus_client 默认 REGISTRY，而是显式建一个 namespace-aware registry，
# 这样测试时可以 ``CollectorRegistry()`` 隔离，避免全局污染导致 ``duplicated timeseries``。
METRICS_REGISTRY = CollectorRegistry()


# ─────────────────────────────────────────────────────────────────────────
# §三 SSE 事件 / 错误计数（v4.1.1 增量 —— 原文未明确，借鉴 §6 SSE 协议必备）
# ─────────────────────────────────────────────────────────────────────────
SSE_EVENTS_TOTAL = Counter(
    "selfwell_sse_events_total",
    "Total SSE events emitted by /assistant endpoints (chat + smart_analyze).",
    ["endpoint", "event_name"],
    registry=METRICS_REGISTRY,
)
SSE_ERRORS_TOTAL = Counter(
    "selfwell_sse_errors_total",
    "Total SSE stream errors emitted (event_name=error or HTTPException mid-stream).",
    ["endpoint", "error_code"],
    registry=METRICS_REGISTRY,
)
SSE_FIRST_BYTE_SECONDS = Histogram(
    "selfwell_sse_first_byte_seconds",
    "Time from request to first SSE byte yielded to client.",
    ["endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=METRICS_REGISTRY,
)


# ─────────────────────────────────────────────────────────────────────────
# §四 LLM 调用 / 延迟（v4.1.1 增量；Step 3.1 仅要求 smart_analyze_* 系列）
# ─────────────────────────────────────────────────────────────────────────
LLM_CALLS_TOTAL = Counter(
    "selfwell_llm_calls_total",
    "Total LLM invocations.",
    ["model", "intent", "is_mock"],
    registry=METRICS_REGISTRY,
)
LLM_LATENCY_SECONDS = Histogram(
    "selfwell_llm_latency_seconds",
    "LLM call latency (seconds).",
    ["model", "intent"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
    registry=METRICS_REGISTRY,
)
VISION_LATENCY_SECONDS = Histogram(
    "selfwell_vision_latency_seconds",
    "Vision LLM call latency (seconds). Excludes rule-engine fallback.",
    ["model", "outcome"],
    buckets=(1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 60.0, 120.0),
    registry=METRICS_REGISTRY,
)
# V5.2.1-PR3 T16：LLM cost 上报（基于 Ark response.usage 估算 + 回退公式）
LLM_COST_YUAN_TOTAL = Counter(
    "selfwell_llm_cost_yuan_total",
    "Cumulative LLM cost in CNY (Ark response.usage 估算；缺则回退公式).",
    ["model", "intent"],
    registry=METRICS_REGISTRY,
)


# ─────────────────────────────────────────────────────────────────────────
# §五 smart_analyze Step 3.1 原始指标（V4 计划正文要求保留）
# ─────────────────────────────────────────────────────────────────────────
SMART_ANALYZE_DONE_TOTAL = Counter(
    "selfwell_smart_analyze_done_total",
    "Total successful smart_analyze completions.",
    ["is_mock"],
    registry=METRICS_REGISTRY,
)
SMART_ANALYZE_FAILED_TOTAL = Counter(
    "selfwell_smart_analyze_failed_total",
    "Total failed smart_analyze.",
    ["stage"],
    registry=METRICS_REGISTRY,
)
SMART_ANALYZE_DURATION_SECONDS = Histogram(
    "selfwell_smart_analyze_duration_seconds",
    "Smart analyze end-to-end duration (seconds).",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0),
    registry=METRICS_REGISTRY,
)


# ─────────────────────────────────────────────────────────────────────────
# §六 渲染函数（Prometheus text exposition）
# ─────────────────────────────────────────────────────────────────────────
def get_metrics() -> tuple[bytes, str]:
    """Render current metrics in Prometheus exposition format.

    Returns:
        ``(body, content_type)`` 二元组：

        - ``body`` —— ``generate_latest(registry)`` 的字节产物
          （``text/plain; version=0.0.4; charset=utf-8``）。
        - ``content_type`` —— ``prometheus_client.CONTENT_TYPE_LATEST``，
          用作 ``GET /metrics`` 路由的 ``media_type``。

    Usage::

        @app.get("/metrics")
        async def metrics() -> Response:
            body, content_type = get_metrics()
            return Response(content=body, media_type=content_type)

    Notes:
        显式 ``b"")`` 让 ``generate_latest`` 返回 ``bytes``；
        Prometheus 抓取端要求 Content-Type 含 ``escaping=allow_utf-8``。
    """
    body = generate_latest(METRICS_REGISTRY)
    return body, CONTENT_TYPE_LATEST


__all__ = [
    # §一 常量
    "VISION_TIMEOUT_SEC",
    # §二 registry
    "METRICS_REGISTRY",
    # §三 SSE
    "SSE_EVENTS_TOTAL",
    "SSE_ERRORS_TOTAL",
    "SSE_FIRST_BYTE_SECONDS",
    # §四 LLM
    "LLM_CALLS_TOTAL",
    "LLM_LATENCY_SECONDS",
    "VISION_LATENCY_SECONDS",
    "LLM_COST_YUAN_TOTAL",  # V5.2.1-PR3 T16
    # §五 smart_analyze
    "SMART_ANALYZE_DONE_TOTAL",
    "SMART_ANALYZE_FAILED_TOTAL",
    "SMART_ANALYZE_DURATION_SECONDS",
    # §六 渲染
    "get_metrics",
]
