"""Phase 4 批次 4 · SSE 首帧 trace_id 注入单测。

覆盖：
- ``assistant_service._sse_pack("start", ...)`` 当 ``app.core.trace`` 注入 trace_id 时，
  首帧 data 必须包含 ``trace_id`` / ``request_id`` 字段（前端断连时反查日志用）。
- ``_sse_pack("token_delta", ...)`` 不强求带 trace_id（避免每帧重复 payload）；
  仅靠 ``event=start`` 注入一次。
- trace 模块不存在 / ContextVar 未设值时，``_sse_pack`` 不抛错。
"""

from __future__ import annotations

from app.services.assistant_service import _sse_pack


def test_sse_pack_start_includes_trace_id_from_contextvar() -> None:
    from app.core.trace import request_id_var, trace_id_var

    request_id_var.set("req-abc")
    trace_id_var.set("trace-xyz")

    frame = _sse_pack("start", {"step": 0})
    assert "trace-xyz" in frame
    assert "req-abc" in frame
    # SSE frame 仍然是合法 "event: start\ndata: {...}\n\n" 形态
    assert frame.startswith("event: start\ndata: ")


def test_sse_pack_start_missing_trace_id_does_not_break() -> None:
    from app.core.trace import request_id_var, trace_id_var

    request_id_var.set(None)
    trace_id_var.set(None)

    frame = _sse_pack("start", {"step": 0})
    # trace_id 字段缺失但 frame 仍能正常发出去（不抛错）
    assert frame.startswith("event: start\ndata: ")
    # 不应把 None 当成字符串写进 payload
    assert '"trace_id": null' not in frame
    assert '"request_id": null' not in frame


def test_sse_pack_non_start_event_keeps_callers_data_unchanged() -> None:
    """非 start 帧：调用方 data 原样保留，不自动注入 trace_id。"""
    from app.core.trace import request_id_var, trace_id_var

    request_id_var.set("req-abc")
    trace_id_var.set("trace-xyz")

    # token_delta 帧：调用方通常只传 {"token": "..."}，不应被自动覆盖
    frame = _sse_pack("token_delta", {"token": "你"})
    # 没注入 trace_id / request_id（仅 start 帧注入）
    assert "trace-xyz" not in frame


def test_sse_pack_handles_trace_module_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """trace 模块不可用时静默（_sse_pack 不能因为导入失败而崩 SSE 主流程）。"""
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "app.core.trace":
            raise ImportError("simulated trace module missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    frame = _sse_pack("start", {"step": 0})
    # 仍然能正常发
    assert frame.startswith("event: start\ndata: ")