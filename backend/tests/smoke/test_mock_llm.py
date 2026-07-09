"""Smoke test — MockLLM + cassette 加载。

简化后用法（monkeypatch）：
    from tests.doubles.mock_llm import MockLLM
    import app.llm
    app.llm.text_llm = MockLLM(default_response="hello")
    app.llm.multimodal_llm = MockLLM(default_response='{"directions":[],"tags":[],"summary":""}')
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def test_mock_llm_returns_predetermined_content() -> None:
    """Mock LLM 默认 response 生效。"""
    from tests.doubles.mock_llm import MockLLM

    async def run() -> None:
        client = MockLLM(default_response="hello world")
        result = await client.ainvoke([HumanMessage(content="hi")])
        assert result.content == "hello world"

    asyncio.run(run())


def test_mock_llm_ainvoke_returns_aimessage() -> None:
    """ainvoke 返回 AIMessage，兼容 LangChain 接口。"""
    from tests.doubles.mock_llm import MockLLM

    async def run() -> None:
        client = MockLLM(default_response="response content")
        result = await client.ainvoke([HumanMessage(content="test")])
        assert isinstance(result, AIMessage)
        assert result.content == "response content"

    asyncio.run(run())


def test_mock_llm_with_response_overrides_default() -> None:
    """with_response 覆盖默认 response。"""
    from tests.doubles.mock_llm import MockLLM

    async def run() -> None:
        client = MockLLM(default_response="default")
        result1 = await client.ainvoke([HumanMessage(content="a")])
        assert result1.content == "default"

        client.with_response("override")
        result2 = await client.ainvoke([HumanMessage(content="b")])
        assert result2.content == "override"

    asyncio.run(run())


def test_mock_llm_record_and_replay() -> None:
    """record() 保存响应，ainvoke() 可命中。"""
    from tests.doubles.mock_llm import MockLLM

    async def run() -> None:
        client = MockLLM(default_response="miss")
        messages = [SystemMessage(content="system"), HumanMessage(content="user")]
        sig = client.record(messages, "recorded response")

        # 首次调用（未命中 cassette，走 default）
        result = await client.ainvoke(messages)
        assert result.content == "recorded response"

    asyncio.run(run())


def test_mock_llm_latency_simulated() -> None:
    """latency_ms 模拟延迟。"""
    import time

    from tests.doubles.mock_llm import MockLLM

    async def run() -> None:
        client = MockLLM(default_response="fast", latency_ms=100)
        start = time.monotonic()
        await client.ainvoke([HumanMessage(content="hi")])
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms >= 90  # 留 10ms 容差

    asyncio.run(run())


def test_mock_llm_multimodal_content() -> None:
    """Mock LLM 可接受多模态格式的 content（list of dicts）。"""
    from tests.doubles.mock_llm import MockLLM

    async def run() -> None:
        client = MockLLM(default_response='{"directions":[],"tags":[],"summary":"ok"}')
        content = [
            {"type": "text", "text": "分析这张图片"},
            {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}},
        ]
        result = await client.ainvoke([HumanMessage(content=content)])
        assert "directions" in result.content

    asyncio.run(run())
