"""V5.2.1-PR4 T22 + F4 · fallback 不返假报告 + SSE end event 透传 is_fallback 测试.

V5.2.1 §3.10 + PR3 evidence §5.2 微调 1：
- `_rule_engine_fallback` 不再返 directions[]/tags[]，改 `is_fallback=true` + `fallback_reason="资料不足"`
- `_stream_smart_analyze` end event payload 透传 is_fallback 字段
- 前端按 §5.2.1 PR4 协议不渲染 report card
"""

from __future__ import annotations

from pathlib import Path
import re


def _read_diagnosis_service_source() -> str:
    src_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "services"
        / "diagnosis_service.py"
    )
    return src_path.read_text(encoding="utf-8")


def _read_assistant_service_source() -> str:
    src_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "services"
        / "assistant_service.py"
    )
    return src_path.read_text(encoding="utf-8")


def test_rule_engine_fallback_returns_is_fallback_true() -> None:
    """T22 + F4：`_rule_engine_fallback` 必须返 `is_fallback=True` 标记.

    改前：返 `{"directions": [...], "tags": [...], "summary": "已为您生成基础养护方向。"}`
    改后：返 `{"is_fallback": True, "fallback_reason": "资料不足", "directions": [], "tags": [], "summary": "请先补充..."}`
    """
    src = _read_diagnosis_service_source()

    # 抽 _rule_engine_fallback 函数体
    func_match = re.search(
        r"def\s+_rule_engine_fallback\((.*?)(?=\n\ndef |\nclass |\Z)",
        src,
        re.DOTALL,
    )
    assert func_match, "diagnosis_service 缺 `_rule_engine_fallback` 函数"
    func_body = func_match.group(0)

    # 改后特征：`is_fallback=True`
    assert re.search(r"is_fallback['\"]?\s*:\s*True", func_body), (
        f"`_rule_engine_fallback` 缺 `is_fallback=True`；body:\n{func_body[:500]}"
    )

    # 改后特征：`fallback_reason="资料不足"` 或 `'资料不足'`
    fallback_reason_cn = "资料不足"
    pattern = r'fallback_reason[\"\']\s*[=:]\s*[\"\'\s]*' + fallback_reason_cn
    assert re.search(pattern, func_body), (
        f"`_rule_engine_fallback` 缺 `fallback_reason=\"{fallback_reason_cn}\"`；body:\n{func_body[:500]}"
    )


def test_rule_engine_fallback_directions_tags_are_empty() -> None:
    """T22 + F4：`_rule_engine_fallback` 必须返空 `directions=[]` + 空 `tags=[]`.

    改前：directions[] 含 3 条 `f"{part} 方向 {i+1}"` 假报告
    改后：directions=[] + tags=[]（前端识别 is_fallback=true 后不渲染 report card）
    """
    src = _read_diagnosis_service_source()

    func_match = re.search(
        r"def\s+_rule_engine_fallback\((.*?)(?=\n\ndef |\nclass |\Z)",
        src,
        re.DOTALL,
    )
    assert func_match
    func_body = func_match.group(0)

    # 返回 dict 内含 `"directions": []` 和 `"tags": []`（空 list）
    assert re.search(r'["\']directions["\']\s*:\s*\[\]', func_body), (
        f"`_rule_engine_fallback` 返回 directions 应为空 list `[]`；body:\n{func_body[:500]}"
    )
    assert re.search(r'["\']tags["\']\s*:\s*\[\]', func_body), (
        f"`_rule_engine_fallback` 返回 tags 应为空 list `[]`；body:\n{func_body[:500]}"
    )


def test_rule_engine_fallback_no_longer_returns_fake_direction_string() -> None:
    """T22 + F4：`_rule_engine_fallback` 不再返 `f"{part} 方向 {i+1}"` 假报告标题.

    V5.2.1 §3.10 改前：directions[].title = `f"{part} 方向 {i+1}"`（垃圾标题）
    V5.2.1 §3.10 + F4 改后：directions=[]，无垃圾标题
    """
    src = _read_diagnosis_service_source()

    func_match = re.search(
        r"def\s+_rule_engine_fallback\((.*?)(?=\n\ndef |\nclass |\Z)",
        src,
        re.DOTALL,
    )
    assert func_match
    func_body = func_match.group(0)

    # 不应再含 `方向 {i+1}` 这种假报告模式
    assert not re.search(r'方向\s*\{\s*i\s*\+\s*1\s*\}', func_body), (
        f"`_rule_engine_fallback` 仍含 `方向 {{i+1}}` 假报告标题模式；body:\n{func_body[:500]}"
    )


def test_smart_analyze_end_event_propagates_is_fallback_when_fallback_triggered() -> None:
    """F4：`_stream_smart_analyze` end event payload 在 fallback 触发时必须含 `is_fallback=True` + `fallback_reason`.

    改前：end event 7 字段不含 is_fallback / fallback_reason
    改后：end_payload["is_fallback"] = payload.get("is_fallback") 透传
    """
    src = _read_assistant_service_source()

    smart_match = re.search(
        r"async def _stream_smart_analyze\((.*?)^(?:async def |def |\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    assert smart_match
    smart_body = smart_match.group(0)

    # 找 end_payload dict 构造段（PR4 改后应该先构造 end_payload dict，再 yield）
    end_payload_match = re.search(
        r"end_payload\s*[:=]",
        smart_body,
    )
    assert end_payload_match, (
        "_stream_smart_analyze 缺 end_payload dict 构造（PR4 F4 必改）"
    )

    # 验证 end_payload 之后 1000 字符内含 `{`
    start = end_payload_match.end()
    block = smart_body[start : start + 1000]
    assert "{" in block[:200], (
        f"end_payload 构造后未跟 dict literal `{{`；block:\n{block[:400]}"
    )

    # 块内必须含 `is_fallback` + `fallback_reason` 透传
    assert "is_fallback" in block, (
        f"end_payload dict 缺 `is_fallback` 字段；block:\n{block[:400]}"
    )
    assert "fallback_reason" in block, (
        f"end_payload dict 缺 `fallback_reason` 字段；block:\n{block[:400]}"
    )


def test_smart_analyze_payload_is_fallback_propagated_from_rule_engine() -> None:
    """F4：`_stream_smart_analyze` 必须读 `payload["is_fallback"]` 并写入 end_payload.

    PR4 F4 关键链路：`_invoke_llm_structured` 返 payload（含 `is_fallback`） → 提取到 end_payload.
    """
    src = _read_assistant_service_source()

    smart_match = re.search(
        r"async def _stream_smart_analyze\((.*?)^(?:async def |def |\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    assert smart_match
    smart_body = smart_match.group(0)

    # V1.1.1 BE-FIX-04：end_payload 直接使用局部变量 is_fallback，不再从 payload["is_fallback"] 中转
    matches = re.findall(
        r'\bis_fallback\b',
        smart_body,
    )
    assert len(matches) >= 2, (
        "_stream_smart_analyze 局部变量 is_fallback 与 end_payload[\"is_fallback\"] 必出现（BE-FIX-04 F4 必改）"
    )