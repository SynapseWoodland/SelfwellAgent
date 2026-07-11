"""V5.2.1-PR4 T20 · chat 路径 safety_passed 真值测试。

与 `test_vision_progress_5_stage.py` 同风格的契约层静态测试：
- 不真启动 DB / LLM（`_stream_chat` 是 async generator + 多依赖）
- 走 importlib + Path 读源码 + 静态正则
- 目的：PR4 修复后能 PASS、修复前 FAIL
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


def _read_diagnosis_service_source() -> str:
    src_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "services"
        / "diagnosis_service.py"
    )
    return src_path.read_text(encoding="utf-8")


def test_chat_path_imports_check_text_safety() -> None:
    """T20：assistant_service 必须从 diagnosis_service import `_check_text_safety`.

    V5.2.1 §3.8 关键约束："不新建 `_check_text_safety`，复用 diagnosis_service.py:53 已有".
    """
    src = _read_assistant_service_source()
    assert re.search(
        r"from\s+app\.services\.diagnosis_service\s+import[^\n]*_check_text_safety",
        src,
    ), "assistant_service 未 import `_check_text_safety` from diagnosis_service"


def test_chat_path_aIMessage_safety_passed_uses_check_text_safety_not_hardcoded_true() -> None:
    """T20：chat 路径 AIMessage 的 `safety_passed=True` 硬编码必须改为真值.

    V5.2.1 §3.8 + §7.1 锚点 #6：
    - 改前：`AIMessage(..., safety_passed=True, ...)` 硬编码
    - 改后：`safety_passed = _check_text_safety(text)["passed"] and to_state != "medical_guarded"`
    """
    src = _read_assistant_service_source()

    # 改前签名不能存在
    hardcoded_pattern = re.compile(
        r"assistant_msg\s*=\s*AIMessage\([^)]*safety_passed\s*=\s*True[^)]*\)",
        re.DOTALL,
    )
    assert not hardcoded_pattern.search(src), (
        "assistant_service 仍有 chat 路径 AIMessage.safety_passed=True 硬编码"
    )

    # 改后特征：`safety_check = _check_text_safety(text)` + `safety_check["passed"]`
    # 或直接 `_check_text_safety(text)["passed"]`（更宽松）
    assert re.search(
        r"_check_text_safety\(\s*text\s*\)",
        src,
    ), "assistant_service 未调 `_check_text_safety(text)`"

    # safety_passed 表达式必须引用 _check_text_safety 结果（直接或间接）
    assert re.search(
        r"safety_passed\s*=.*?(?:safety_check|_check_text_safety)",
        src,
    ), (
        "chat 路径 safety_passed= 赋值未引用 _check_text_safety 或 safety_check 真值"
    )


def test_diagnosis_service_check_text_safety_signature() -> None:
    """T20：`_check_text_safety` 函数签名契约.

    路径：diagnosis_service.py:53. 改前/改后都应有此签名；PR4 不动这个函数（仅复用）。
    """
    src = _read_diagnosis_service_source()
    match = re.search(
        r"def\s+_check_text_safety\(\s*text\s*:\s*str\s*\)\s*->\s*dict",
        src,
    )
    assert match, "diagnosis_service.py:53 `_check_text_safety(text: str) -> dict` 签名丢失"