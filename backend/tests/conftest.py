"""Pytest 配置 — 所有 unit/smoke 测试共享的 fixtures。"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """所有测试默认注入 MockLLM，避免真实 LLM 调用。

    在需要真实 LLM 的集成测试中，用 ``monkeypatch.setenv("SELFWELL_USE_MOCK_LLM", "0")``
    或手动 patch ``app.llm.*_llm`` 来覆盖。
    """
    from tests.doubles.mock_llm import MockLLM

    try:
        import app.llm as app_llm  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        return  # 无 LLM 依赖时跳过（如 ack_compliance 等纯文档测试）

    mock_text = MockLLM(default_response="(mocked reply)")
    mock_multi = MockLLM(
        default_response='{"directions":[{"title":"mock","description":"mock","video_id":null}],"tags":["mock"],"summary":"mock","llm_cost":"0"}'
    )
    monkeypatch.setattr(app_llm, "text_llm", mock_text, raising=True)
    monkeypatch.setattr(app_llm, "multimodal_llm", mock_multi, raising=True)
    monkeypatch.setattr(app_llm, "llm", mock_text, raising=True)
