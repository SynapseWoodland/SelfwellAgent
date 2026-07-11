"""V5.2.1-PR4 T21 · smart_analyze 路径 medical_reject 短路测试.

契约层静态测试：
- `_stream_smart_analyze` 在 `:707` 前必须有 `_check_text_safety(text)` 早返
- 命中时 yield SSE error 帧（`code=E_ASSISTANT_MEDICAL_REJECT`）+ 不 yield 后续 progress/report/end
- audit_persona_state_switch 必调（合规审计 3 事件之一）
"""

from __future__ import annotations

from pathlib import Path
import re


def _read_assistant_service_source() -> str:
    src_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "services"
        / "assistant_service.py"
    )
    return src_path.read_text(encoding="utf-8")


def _extract_smart_analyze_body(src: str) -> str:
    """抽取 `_stream_smart_analyze` 函数体（含函数签名）。"""
    smart_match = re.search(
        r"async def _stream_smart_analyze\((.*?)^(?:async def |def |class |\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    assert smart_match, "_stream_smart_analyze 函数不存在"
    return smart_match.group(0)


def _extract_medical_reject_block(smart_body: str) -> str:
    """从 `_stream_smart_analyze` 函数体抽取 `if not safety_check["passed"]:` 整个块.

    边界：直到下一个 0-缩进顶级语句或函数结尾。
    """
    start_match = re.search(
        r'if\s+not\s+safety_check\[["\']passed["\']\]\s*:\s*\n',
        smart_body,
    )
    if start_match is None:
        return ""
    start = start_match.end()
    next_top = re.search(
        r"^(?:async def |def |class )",
        smart_body[start:],
        re.MULTILINE,
    )
    end = start + next_top.start() if next_top else len(smart_body)
    return smart_body[start:end]


def test_smart_analyze_has_medical_reject_short_circuit() -> None:
    """T21：`_stream_smart_analyze` 在 profile dict 构造前必须有 medical_reject 短路.

    改前：直接构造 profile，没早返
    改后：
    ```python
    safety_check = _check_text_safety(text)
    if not safety_check["passed"]:
        ...yield _sse_pack("error", {"code": E_ASSISTANT_MEDICAL_REJECT, ...})
        ...return
    ```
    """
    src = _read_assistant_service_source()
    smart_body = _extract_smart_analyze_body(src)

    early_return_match = re.search(
        r'if\s+not\s+safety_check\[["\']passed["\']\]\s*:',
        smart_body,
    )
    assert early_return_match, (
        "_stream_smart_analyze 缺 medical_reject 短路（`if not safety_check[\"passed\"]:`）"
    )

    profile_match = re.search(
        r'profile\s*=\s*\{[^}]*age_range',
        smart_body,
    )
    assert profile_match, "_stream_smart_analyze 缺 profile dict 构造"

    assert early_return_match.start() < profile_match.start(), (
        "medical_reject 短路位置必须在 profile dict 构造之前（否则 vision LLM 已白调）"
    )


def test_smart_analyze_medical_reject_error_frame_uses_assistant_medical_reject_code() -> None:
    """T21：medical_reject 短路的 error 帧 code 必须是 `E_ASSISTANT_MEDICAL_REJECT`.

    V5.2.1 §3.9 约束：错误码统一从 `app.errors.codes` import，不硬编码字符串.
    """
    src = _read_assistant_service_source()
    smart_body = _extract_smart_analyze_body(src)
    block = _extract_medical_reject_block(smart_body)
    assert block, "medical_reject 短路块抽不出"

    assert "E_ASSISTANT_MEDICAL_REJECT" in block, (
        f"medical_reject 短路 error 帧缺 `E_ASSISTANT_MEDICAL_REJECT` 引用；block:\n{block[:300]}"
    )


def test_smart_analyze_medical_reject_calls_audit_persona_state_switch() -> None:
    """T21：medical_reject 短路必须调 `audit_persona_state_switch`（合规审计 3 事件之一，ADR-0015 §2.4.4）.

    改前：完全没调
    改后：调用 audit_persona_state_switch 记录 trigger=smart_analyze_medical_reject_short_circuit
    """
    src = _read_assistant_service_source()
    smart_body = _extract_smart_analyze_body(src)
    block = _extract_medical_reject_block(smart_body)
    assert block

    assert "audit_persona_state_switch" in block, (
        f"medical_reject 短路未调 `audit_persona_state_switch`（合规审计要求）；block:\n{block[:300]}"
    )


def test_smart_analyze_medical_reject_short_circuit_yields_error_frame_only() -> None:
    """T21：medical_reject 短路 yield SSE error 帧（不再 yield 后续 progress/report/end）.

    短路块内必须 `_sse_pack("error", ...)`；return 必须存在。
    """
    src = _read_assistant_service_source()
    smart_body = _extract_smart_analyze_body(src)
    block = _extract_medical_reject_block(smart_body)
    assert block

    assert '_sse_pack("error"' in block, (
        f"medical_reject 短路未 yield SSE error 帧；block:\n{block[:300]}"
    )
    assert "return" in block, (
        f"medical_reject 短路缺 return（继续 yield 后续 progress/report/end）；block:\n{block[:300]}"
    )