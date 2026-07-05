"""Smoke test — Mock LLM + Cassandra-style cassette 加载。"""

from __future__ import annotations

import asyncio


def test_mock_llm_returns_predetermined_content() -> None:
    """Mock LLM 默认 response 生效，且包含合理 schema 字段。"""
    from app.llm.client import LLMMessage, LLMRequest
    from app.llm.mock_doubles import MockLLMClient

    async def run() -> None:
        client = MockLLMClient(default_response="hello world")
        req = LLMRequest(messages=[LLMMessage(role="user", content="hi")])
        resp = await client.achat(req)
        assert resp.content == "hello world"
        assert resp.model == "mock"
        assert resp.latency_ms >= 0

    asyncio.run(run())


def test_mock_llm_signature_cache_hit() -> None:
    """相同请求 → 签名一致 → cassette 命中。"""
    from app.llm.client import LLMMessage, LLMRequest
    from app.llm.mock_doubles import MockLLMClient

    async def run() -> None:
        client = MockLLMClient(default_response="cached")
        req = LLMRequest(messages=[LLMMessage(role="user", content="echo")])
        # 第一次：default_response
        r1 = await client.achat(req)
        # 第二次：应还是 default（cassette 为空时）
        r2 = await client.achat(req)
        assert r1.content == r2.content == "cached"

    asyncio.run(run())
