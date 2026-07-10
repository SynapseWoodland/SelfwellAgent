"""llm_cost Prometheus Counter + diagnosis_service 接入 单测（V5.2.1-PR3 T16）。

注：prometheus_client Counter 命名自动加 `_total` 后缀：
  Counter("selfwell_llm_cost_yuan_total", ...) 实测 _name = "selfwell_llm_cost_yuan"
  显示时 metrics 文本格式仍按 full name。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.metrics import LLM_COST_YUAN_TOTAL


def test_llm_cost_yuan_total_counter_registered_with_correct_labels() -> None:
    """T16：Counter 注册实名为 selfwell_llm_cost_yuan（自动去 _total 后缀）+ (model, intent) 标签."""
    # prometheus_client Counter 命名规约：构造参数 'selfwell_llm_cost_yuan_total'
    # 实测存储为 'selfwell_llm_cost_yuan'（自动剥 _total 后缀），
    # exposition 时追加 _total 写回。
    name = LLM_COST_YUAN_TOTAL._name  # type: ignore[attr-defined]
    assert name == "selfwell_llm_cost_yuan", (
        f"Counter 内部名应为 selfwell_llm_cost_yuan（prometheus_client 自动剥 _total），"
        f"实为 {name}"
    )

    label_names = list(LLM_COST_YUAN_TOTAL._labelnames)  # type: ignore[attr-defined]
    assert label_names == ["model", "intent"]


def test_llm_cost_yuan_total_inc_works() -> None:
    """T16：Counter.labels(model, intent).inc(cost) 可累计."""
    LLM_COST_YUAN_TOTAL.labels(model="rule-engine-test-inc", intent="test_intent").inc(0.001)
    val = LLM_COST_YUAN_TOTAL.labels(
        model="rule-engine-test-inc", intent="test_intent"
    )._value.get()
    assert val >= 0.001


def test_diagnose_path_registers_llm_cost_via_metrics_module() -> None:
    """diagnosis_service._invoke_llm_structured 接入 LLM_COST_YUAN_TOTAL 上报路径存在.

    静态校验而非端到端：因 multimodal_llm.with_structured_output 是真 SDK 调用，
    不易 mock；改为 source-level 验证 metrics module + .labels() 调用链。
    """
    import inspect

    from app.services import diagnosis_service

    src = inspect.getsource(diagnosis_service._invoke_llm_structured)
    assert "LLM_COST_YUAN_TOTAL" in src, (
        "_invoke_llm_structured 应引用 LLM_COST_YUAN_TOTAL Counter"
    )
    assert 'intent="vision_diagnose"' in src, (
        "_invoke_llm_structured 应以 intent='vision_diagnose' 上报（V5.2.1 §3.6 约定）"
    )
    assert ".inc(" in src, "_invoke_llm_structured 应触发 .inc() 方法"
