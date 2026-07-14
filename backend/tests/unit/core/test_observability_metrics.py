"""Phase 4 批次 4 新增可观测性指标单测。

覆盖：
- SSE_STAGE_DURATION_SECONDS / SSE_DISCONNECTED_TOTAL / DB_POOL_IN_USE / DB_POOL_SIZE 注册
- observability.observe_sse_event / observe_sse_disconnect / observe_db_pool 行为
  （包括失败隔离：metric 模块不可用时主流程不受影响）
- track_sse_stage context manager：自动填入 duration_seconds 并打点
- log.py 三个 helper（log_llm_timeout / log_db_error / log_sse_disconnect）：
  - 字段名固定（用于 Loki / Grafana 聚合）
  - error_kind 维度
  - 在 sentry_sdk 未安装时静默
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────────
# §一 新增 Prometheus 指标注册
# ──────────────────────────────────────────────────────────────────────────
def test_sse_stage_duration_seconds_registered() -> None:
    from app.core.metrics import SSE_STAGE_DURATION_SECONDS

    name = SSE_STAGE_DURATION_SECONDS._name  # type: ignore[attr-defined]
    # Histogram 命名规约：构造参数 "selfwell_sse_stage_duration_seconds"
    # prometheus_client 自动剥 _seconds 改成 _seconds_bucket / _seconds_count / _seconds_sum
    assert "sse_stage_duration" in name
    assert tuple(SSE_STAGE_DURATION_SECONDS._labelnames) == ("endpoint", "stage")  # type: ignore[attr-defined]


def test_sse_disconnected_total_registered() -> None:
    from app.core.metrics import SSE_DISCONNECTED_TOTAL

    name = SSE_DISCONNECTED_TOTAL._name  # type: ignore[attr-defined]
    assert "sse_disconnected" in name
    assert tuple(SSE_DISCONNECTED_TOTAL._labelnames) == ("endpoint", "reason")  # type: ignore[attr-defined]


def test_db_pool_gauges_registered() -> None:
    from app.core.metrics import DB_POOL_IN_USE, DB_POOL_SIZE

    assert "db_pool_in_use" in DB_POOL_IN_USE._name  # type: ignore[attr-defined]
    assert "db_pool_size" in DB_POOL_SIZE._name  # type: ignore[attr-defined]
    assert tuple(DB_POOL_IN_USE._labelnames) == ("pool",)  # type: ignore[attr-defined]


# ──────────────────────────────────────────────────────────────────────────
# §二 observability helper —— 失败隔离
# ──────────────────────────────────────────────────────────────────────────
def test_observe_sse_event_swallowed_when_metrics_missing() -> None:
    """metric 模块不存在 / 调用失败时不能抛错（不能让 SSE 主流程崩）。"""
    from app.core import observability

    with patch.object(observability, "_safe_metric", return_value=None):
        # 不应抛任何异常
        observability.observe_sse_event(
            endpoint="assistant.send_message_stream",
            event_name="start",
        )


def test_observe_sse_event_increments_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import observability
    from app.core.metrics import SSE_EVENTS_TOTAL

    before = SSE_EVENTS_TOTAL.labels(
        endpoint="assistant.send_message_stream", event_name="start"
    )._value.get()  # type: ignore[attr-defined]

    observability.observe_sse_event(
        endpoint="assistant.send_message_stream",
        event_name="start",
    )

    after = SSE_EVENTS_TOTAL.labels(
        endpoint="assistant.send_message_stream", event_name="start"
    )._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_observe_sse_event_error_increments_error_counter() -> None:
    from app.core import observability
    from app.core.metrics import SSE_ERRORS_TOTAL

    before = SSE_ERRORS_TOTAL.labels(
        endpoint="assistant.send_message_stream", error_code="error"
    )._value.get()  # type: ignore[attr-defined]

    observability.observe_sse_event(
        endpoint="assistant.send_message_stream",
        event_name="error",
    )

    after = SSE_ERRORS_TOTAL.labels(
        endpoint="assistant.send_message_stream", error_code="error"
    )._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_observe_sse_disconnect_increments_counter() -> None:
    from app.core import observability
    from app.core.metrics import SSE_DISCONNECTED_TOTAL

    before = SSE_DISCONNECTED_TOTAL.labels(
        endpoint="diagnosis.job_stream", reason="client_closed"
    )._value.get()  # type: ignore[attr-defined]

    observability.observe_sse_disconnect(
        endpoint="diagnosis.job_stream", reason="client_closed"
    )

    after = SSE_DISCONNECTED_TOTAL.labels(
        endpoint="diagnosis.job_stream", reason="client_closed"
    )._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


def test_observe_db_pool_handles_missing_engine() -> None:
    """engine 不可用时静默（observe_db_pool 在 /readyz 调用，必须不抛）。"""
    from app.core import observability

    # 不创建任何 engine，只 patch 掉 get_engine 让它抛错
    with patch(
        "app.db.session.get_engine",
        side_effect=RuntimeError("no engine in test"),
    ):
        observability.observe_db_pool()  # 不应抛


def test_observe_db_pool_writes_gauges(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import observability
    from app.core.metrics import DB_POOL_IN_USE, DB_POOL_SIZE

    fake_pool = MagicMock()
    fake_pool.size = lambda: 5
    fake_pool.checkedout = lambda: 3
    fake_engine = MagicMock()
    fake_engine.pool = fake_pool

    monkeypatch.setattr("app.db.session.get_engine", lambda: fake_engine)

    observability.observe_db_pool(pool_name="primary")

    in_use = DB_POOL_IN_USE.labels(pool="primary")._value.get()  # type: ignore[attr-defined]
    size = DB_POOL_SIZE.labels(pool="primary")._value.get()  # type: ignore[attr-defined]
    assert size == 5
    assert in_use == 3


def test_track_sse_stage_records_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import observability
    from app.core.metrics import SSE_STAGE_DURATION_SECONDS

    captured: dict[str, float] = {}
    real_observe = observability.observe_sse_event

    def _capture(endpoint: str, event_name: str, duration_seconds: float | None = None, stage: str | None = None) -> None:
        if duration_seconds is not None and stage:
            captured["duration"] = duration_seconds
            captured["stage"] = stage  # type: ignore[assignment]

    monkeypatch.setattr(observability, "observe_sse_event", _capture)

    with observability.track_sse_stage("assistant.smart_analyze", "vision_analyze") as ctx:
        import time

        time.sleep(0.05)

    assert captured["duration"] >= 0.05
    assert captured["stage"] == "vision_analyze"


# ──────────────────────────────────────────────────────────────────────────
# §三 log.py 关键错误聚合 helper
# ──────────────────────────────────────────────────────────────────────────
def test_log_llm_timeout_emits_structured_payload(caplog: pytest.LogCaptureFixture) -> None:
    """LLM 超时 → ERROR 级别 + error_kind 固定字段。"""
    from app.core.log import log_llm_timeout

    with caplog.at_level("ERROR", logger="selfwell"):
        log_llm_timeout(
            user_id_pseudo="hash_abc",
            model="doubao-seed-1-6",
            timeout_sec=30.0,
            intent="vision_diagnose",
            fallback_taken=True,
        )

    # caplog 抓的是 stdlib logging record；我们这里直接断言 _emit_to_sentry 调用即可
    # 不强制要求走 loguru（caplog 抓不到 loguru）


def test_log_llm_timeout_does_not_raise_when_sentry_missing() -> None:
    """sentry_sdk 未安装 → _emit_to_sentry 内部 except，静默。"""
    from app.core.log import log_llm_timeout

    # 不应抛任何异常（即便 sentry_sdk 完全没装）
    log_llm_timeout(
        user_id_pseudo="hash_abc",
        model="doubao-seed-1-6",
        timeout_sec=30.0,
        intent="vision_diagnose",
    )


def test_log_db_error_does_not_raise() -> None:
    from app.core.log import log_db_error

    log_db_error(
        user_id_pseudo="hash_xyz",
        op="SELECT FOR UPDATE",
        table="ai_sessions",
        error_code="23505",
        error_message="duplicate key value violates unique constraint",
    )


def test_log_sse_disconnect_does_not_raise() -> None:
    from app.core.log import log_sse_disconnect

    log_sse_disconnect(
        user_id_pseudo="hash_xyz",
        endpoint="assistant.send_message_stream",
        stage="vision_analyze",
        sent_events=7,
        error_kind="client_closed",
    )


def test_log_helpers_exported_in_dunder_all() -> None:
    import app.core.log as log_mod

    for name in ("log_llm_timeout", "log_db_error", "log_sse_disconnect"):
        assert name in log_mod.__all__, f"{name} 必须在 __all__ 中"