"""V5.2.1-PR4 T20 · smart_analyze 路径 safety_passed 真值测试.

契约层静态测试：`_stream_smart_analyze` 内 AIMessage.safety_passed 必须从 `_check_text_safety` 取真值，不再硬编码 True / 不再缺字段（Pydantic 默认）。
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


def test_smart_analyze_aIMessage_has_safety_passed_field() -> None:
    """T20：`_stream_smart_analyze` AIMessage 必须显式含 `safety_passed=<expression>` 字段.

    改前：assistant_msg = AIMessage(...) 不含 safety_passed（依赖 Pydantic 默认 True）
    改后：必须显式 `safety_passed=...`（取自 `_check_text_safety(text)`）
    """
    src = _read_assistant_service_source()

    # 抽 _stream_smart_analyze 函数体（直到下一个顶级 def 或文件末尾）
    smart_match = re.search(
        r"async def _stream_smart_analyze\((.*?)^(?:async def |def |\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    assert smart_match, "assistant_service 缺 _stream_smart_analyze 函数"
    smart_body = smart_match.group(0)

    # AIMessage(...) 实例化必须显式含 safety_passed=
    aimsg_match = re.search(
        r"assistant_msg\s*=\s*AIMessage\(",
        smart_body,
    )
    assert aimsg_match, "_stream_smart_analyze 缺 AIMessage 落库"

    start = aimsg_match.end()
    block = smart_body[start : start + 1000]
    assert "safety_passed=" in block, (
        "_stream_smart_analyze AIMessage 缺 `safety_passed=` 字段（依赖 Pydantic 默认值）"
    )


def test_smart_analyze_safety_passed_uses_check_text_safety() -> None:
    """T20：`_stream_smart_analyze` 内 `_check_text_safety(text)` 必须被调用，且结果用于 safety_passed.

    改前：完全没调
    改后：调 `_check_text_safety(text)["passed"]` 至少 1 次（在 :707 前 medical_reject 短路 + 在 :785-800 AIMessage 落库）
    """
    src = _read_assistant_service_source()

    # 至少 1 处调 _check_text_safety(text)
    matches = re.findall(
        r'_check_text_safety\(\s*text\s*\)',
        src,
    )
    assert len(matches) >= 1, (
        "assistant_service 未调 `_check_text_safety(text)`（chat + smart_analyze 双路径至少 1 处）"
    )


def test_smart_analyze_aIMessage_safety_passed_references_passed_attribute() -> None:
    """T20：`_stream_smart_analyze` AIMessage.safety_passed 必须等于 `_check_text_safety(text)["passed"]` 的真值.

    严格匹配：AIMessage(..., safety_passed=<expr>, ...) 中 <expr> 包含 _check_text_safety
    """
    src = _read_assistant_service_source()

    smart_match = re.search(
        r"async def _stream_smart_analyze\((.*?)^(?:async def |def |\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    assert smart_match
    smart_body = smart_match.group(0)

    aimsg_match = re.search(
        r"assistant_msg\s*=\s*AIMessage\(",
        smart_body,
    )
    assert aimsg_match
    start = aimsg_match.end()
    block = smart_body[start : start + 1000]

    # AIMessage(...) 中 safety_passed=... 的赋值表达式
    safety_match = re.search(
        r"safety_passed\s*=\s*([^\n,]+)",
        block,
    )
    assert safety_match, "_stream_smart_analyze AIMessage.safety_passed= 赋值表达式缺失"
    safety_expr = safety_match.group(1).strip()

    # 该表达式要么是 _check_text_safety(text)["passed"]
    # 要么是形如 safety_check["passed"] / safety_check.get("passed") 等局部变量（更宽松）
    assert "_check_text_safety" in safety_expr or "safety_check" in safety_expr, (
        f"_stream_smart_analyze AIMessage.safety_passed={safety_expr} 不是真值（应取自 _check_text_safety 或 safety_check）"
    )