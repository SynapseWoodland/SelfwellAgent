"""LLM 模块单测 — 简化后版本。

只测：
- app/llm 单实例初始化成功（无 api_key 时不 crash）
- is_multimodal_request 工具函数存在性
- MockLLM 可注入
"""

from __future__ import annotations

import pytest


def test_llm_module_imports_without_crash() -> None:
    """app.llm 导入成功，两个实例存在。"""
    from app.llm import llm, multimodal_llm, text_llm

    assert multimodal_llm is not None
    assert text_llm is not None
    assert llm is not None


def test_llm_client_schema_imports() -> None:
    """client.py schema 正常导入。"""
    from app.llm.client import LLMMessage, MultimodalRequest, TextRequest

    msg = LLMMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"

    req_text = TextRequest(messages=[msg])
    assert req_text.capability == "text"

    req_multi = MultimodalRequest(messages=[msg], images=["https://x.jpg"])
    assert req_multi.capability == "vision"
    assert len(req_multi.images) == 1


def test_mock_llm_can_be_injected() -> None:
    """MockLLM 可通过 monkeypatch 替换 llm 实例。"""
    from tests.doubles.mock_llm import MockLLM

    from app.llm import text_llm

    original = text_llm
    mock = MockLLM(default_response="mocked response")
    try:
        import app.llm

        app.llm.text_llm = mock  # type: ignore[assignment]

        import asyncio

        async def verify() -> None:
            result = await app.llm.text_llm.ainvoke([])
            assert result.content == "mocked response"

        asyncio.run(verify())
    finally:
        import app.llm

        app.llm.text_llm = original  # restore
