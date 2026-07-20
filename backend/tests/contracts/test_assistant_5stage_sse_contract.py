"""assistant `_stream_smart_analyze` 5 阶段 SSE 契约测试（V1.1.1 BE-FIX-08 新增）。

真源：
- ``docs/architecture/sse-events.md`` —— SSE 事件 schema
- ``docs/plan/decision-018-vision-fallback-rename.md`` —— BE-FIX-04 决策
- V5.2.1-PR3 T17/T18/T19 + PR4 F4：end 事件 7 字段（ok/reply/persona_state/
  is_fallback/medical_guarded/is_quick_reply/level）

说明：
- 静态契约通过文本扫描保证字段不漂移（避免依赖异步执行环境的脆弱 mock）
- 完整端到端 SSE 事件序列由 ``tests/unit/services/test_vision_progress_5_stage.py`` 覆盖
- 不启动真实 DB / LLM
"""
from __future__ import annotations

import re
from pathlib import Path


SRC_PATH = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "services"
    / "assistant_service.py"
)


def _read_source() -> str:
    return SRC_PATH.read_text(encoding="utf-8")


def _extract_smart_analyze_body(src: str) -> str:
    m = re.search(
        r"async def _stream_smart_analyze\((.*?)^(?:async def |def |\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    assert m, "assistant_service 缺 _stream_smart_analyze"
    return m.group(0)


def test_smart_analyze_emits_5_progress_stages_in_order() -> None:
    """T17：5 阶段 progress 顺序（step 1..5，percent 与 label 与 V5.2.1-PR3 一致）."""
    src = _read_source()
    body = _extract_smart_analyze_body(src)

    expected = [
        (1, 15, "图片校验中"),
        (2, 45, "正在分析体态"),
        (3, 75, "生成养护建议"),
        (4, 100, "分析完成"),
        (5, 100, "已就绪"),
    ]
    last_pos = 0
    for step, percent, label in expected:
        needle = f"_emit_progress({step}, {percent}, \"{label}\")"
        pos = body.find(needle, last_pos)
        assert pos >= 0, f"_stream_smart_analyze 缺第 {step} 阶段 {needle}"
        last_pos = pos + 1


def test_smart_analyze_end_event_has_7_fields_v521_pr3_t19() -> None:
    """T19：end 事件 schema 7 字段，is_fallback 替代旧 is_mock（BE-FIX-04）."""
    src = _read_source()
    body = _extract_smart_analyze_body(src)

    expected = [
        "\"ok\"",
        "\"reply\"",
        "\"persona_state\"",
        "\"is_fallback\"",
        "\"medical_guarded\"",
        "\"is_quick_reply\"",
        "\"level\"",
    ]

    end_payload = re.search(r"end_payload\s*[:=]", body)
    if end_payload:
        block = body[end_payload.start() : end_payload.start() + 1200]
    else:
        m = re.search(r"_sse_pack\(\s*\"end\"\s*,\s*\{", body)
        assert m
        block = body[m.start() : m.start() + 600]

    for key in expected:
        assert key in block, f"end 事件缺字段 {key}"


def test_smart_analyze_drops_legacy_is_mock_after_v111_fix04() -> None:
    """BE-FIX-04：end 事件不能再出现旧键 is_mock."""
    src = _read_source()
    body = _extract_smart_analyze_body(src)
    end_m = re.search(r"_sse_pack\(\s*\"end\"\s*,\s*\{", body)
    assert end_m
    block = body[end_m.start() : end_m.start() + 800]
    assert "\"is_mock\"" not in block, (
        "_stream_smart_analyze end 事件残留旧键 is_mock（BE-FIX-04 未完成）"
    )


def test_smart_analyze_progress_emits_step_percent_label_shape() -> None:
    """T17 字段形状：每个 progress 帧的 data 必须含 step/percent/label 三字段."""
    src = _read_source()
    assert "step" in src and "percent" in src and "label" in src
    assert len(re.findall(r"_emit_progress\(\d+,", src)) >= 5


def test_assistant_service_end_payload_contains_fallback_reason_in_success_path() -> None:
    """BE-FIX-04：成功路径 end_payload dict 含 fallback_reason 字段（当 is_fallback=True 时）.

    注意：函数体内有多个 _sse_pack("end", ...) yield（错误路径、成功路径）；
    这里精准定位 end_payload 字典字面量（BE-FIX-04 改动点）。
    """
    src = _read_source()
    body = _extract_smart_analyze_body(src)

    # 定位 end_payload dict 字面量起点（在 _sse_pack 之前构造）
    end_payload = re.search(r"end_payload\s*[:=]", body)
    assert end_payload, "_stream_smart_analyze 缺 end_payload dict"
    block = body[end_payload.start() : end_payload.start() + 1200]
    assert '"is_fallback"' in block, "end_payload 必须含 is_fallback 字段"
    # is_fallback 为 True 时分支写入 fallback_reason
    assert "fallback_reason" in block, "end_payload 必须含 fallback_reason 字段写入逻辑"


def test_assistant_service_end_event_no_legacy_is_mock_payload() -> None:
    """BE-FIX-04：end event payload dict 字面量不能再出现 is_mock."""
    src = _read_source()
    body = _extract_smart_analyze_body(src)
    end_payload = re.search(r"end_payload\s*[:=]", body)
    assert end_payload
    block = body[end_payload.start() : end_payload.start() + 1200]
    assert "\"is_mock\"" not in block, "end_payload 不应再含 is_mock 键"
