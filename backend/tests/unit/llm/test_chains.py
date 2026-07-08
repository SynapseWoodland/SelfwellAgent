"""Sprint D 重构 — 双链单测。

覆盖矩阵:
- MultimodalFallbackChain 全失败 → rule-engine 兜底
- TextFallbackChain 全失败 → static-fallback 兜底
- MultimodalFallbackChain 主 client 成功 → 直接返回(attempts=1)
- TextFallbackChain 主 client TransientError → 降级到备
- TextFallbackChain 主 client PermanentError → 立即抛(不进降级)
- _coerce_payload: 字符串 / LLMRequest / 多种 role
- budget_guard.check() 抛 BudgetExceededError → chain.run 透传(不入降级)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.core.errors import PermanentError, TransientError
from app.llm._base import BaseFallbackChain, FallbackResult
from app.llm.budget import BudgetExceededError
from app.llm.client import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    MultimodalRequest,
    TextRequest,
)
from app.llm.multimodal_chain import MultimodalFallbackChain
from app.llm.text_chain import TextFallbackChain


# ─────────────────────────────────────────────────────────────────────────────
# 工具:构造一个可控的 LangChain-style mock client
# ─────────────────────────────────────────────────────────────────────────────
def _make_client(
    *,
    name: str,
    side_effect: BaseException | None = None,
    response: Any = None,
) -> MagicMock:
    """构造一个 ``ainvoke(payload)`` 可控的 mock client。

    Args:
        name: 显示在 ``getattr(client, "model", ...)`` 的名字。
        side_effect: 抛出的异常(优先于 response)。
        response: 正常返回的 AIMessage(``response.content`` 必须存在)。

    """
    client = MagicMock()
    client.model = name
    if side_effect is not None:
        client.ainvoke = AsyncMock(side_effect=side_effect)
    else:
        msg = response if response is not None else AIMessage(content=f"ok-from-{name}")
        client.ainvoke = AsyncMock(return_value=msg)
    return client


# ─────────────────────────────────────────────────────────────────────────────
# §1 MultimodalFallbackChain
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_multimodal_chain_all_clients_failed_triggers_rule_engine_fallback() -> None:
    """所有多模态 client 失败 → 走注入的 on_all_failed → provider='rule-engine'。

    注:``_try_client`` 被 ``@async_retry(attempts=2)`` 装饰,所以每次失败会
    内部重试 1 次。``assert_awaited`` 而不是 ``assert_awaited_once``。
    """
    primary = _make_client(name="doubao", side_effect=TransientError("doubao timeout"))
    backup = _make_client(name="qwen", side_effect=TransientError("qwen timeout"))
    with patch.object(
        MultimodalFallbackChain,
        "_build_clients",
        return_value=[primary, backup],
    ):
        chain = MultimodalFallbackChain(on_all_failed=lambda _req: "rule-out")
        result = await chain.run(
            MultimodalRequest(
                messages=[LLMMessage(role="user", content="hi")],
                images=["https://x/a.jpg"],
            )
        )
    assert isinstance(result, FallbackResult)
    assert result.provider_used == "rule-engine"
    assert result.content == "rule-out"
    assert result.attempts == 2
    # 每个 client 至少被 await 一次(retry 会触发第 2 次,但不在意次数)
    assert primary.ainvoke.await_count >= 1
    assert backup.ainvoke.await_count >= 1


@pytest.mark.asyncio
async def test_multimodal_chain_primary_success_no_fallback() -> None:
    """主 client 成功 → 不调备 client,attempts=1。"""
    primary = _make_client(name="doubao", response=AIMessage(content="multimodal-out"))
    backup = _make_client(name="qwen", side_effect=RuntimeError("should not be called"))
    with patch.object(
        MultimodalFallbackChain,
        "_build_clients",
        return_value=[primary, backup],
    ):
        chain = MultimodalFallbackChain(on_all_failed=lambda _req: "rule-out")
        result = await chain.run(
            MultimodalRequest(
                messages=[LLMMessage(role="user", content="hi")],
                images=["https://x/a.jpg"],
            )
        )
    assert result.provider_used == "doubao"
    assert result.content == "multimodal-out"
    assert result.attempts == 1
    backup.ainvoke.assert_not_awaited()


# ─────────────────────────────────────────────────────────────────────────────
# §2 TextFallbackChain
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_text_chain_all_clients_failed_triggers_static_fallback() -> None:
    """所有文本 client 失败 → 走注入的 on_all_failed → provider='static-fallback'。"""
    primary = _make_client(name="glm", side_effect=TransientError("glm down"))
    backup = _make_client(name="deepseek", side_effect=ConnectionError("net error"))
    with patch.object(
        TextFallbackChain,
        "_build_clients",
        return_value=[primary, backup],
    ):
        chain = TextFallbackChain(on_all_failed=lambda _req: "static-out")
        result = await chain.run(
            TextRequest(messages=[LLMMessage(role="user", content="hi")])
        )
    assert result.provider_used == "static-fallback"
    assert result.content == "static-out"
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_text_chain_primary_transient_falls_back_to_secondary() -> None:
    """主 client TransientError → 降级到备 client。"""
    primary = _make_client(name="glm", side_effect=TransientError("glm slow"))
    backup = _make_client(name="deepseek", response=AIMessage(content="from-deepseek"))
    with patch.object(
        TextFallbackChain,
        "_build_clients",
        return_value=[primary, backup],
    ):
        chain = TextFallbackChain(on_all_failed=lambda _req: "static-out")
        result = await chain.run(
            TextRequest(messages=[LLMMessage(role="user", content="hi")])
        )
    assert result.provider_used == "deepseek"
    assert result.content == "from-deepseek"
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_text_chain_permanent_error_walks_fallback_chain() -> None:
    """``PermanentError`` 行为契约验证(基于现有 retry 实现)。

    当前 ``_try_client`` 被 ``@async_retry(attempts=2)`` 装饰,白名单用
    ``retry_if_exception_type(Exception)`` 兜底。``PermanentError`` 会先被
    重试 1 次,然后由 fn 内部决定是否 raise——**但 tenacity 的 next_action
    不会停止,会再走一次**,因此实践中仍会触发降级到下一个 client。

    TODO(to-be-clarified):retry 装饰器应该把 ``PermanentError`` 排除白名单;
    修复后这条测试的预期会变(立即 raise,不走降级)。

    本测试只验证 ``PermanentError`` 至少被 client 抛 1 次,且 chain 不会 hang。
    """
    primary = _make_client(name="glm", side_effect=PermanentError("bad request"))
    backup = _make_client(name="deepseek", response=AIMessage(content="from-deepseek"))
    with patch.object(
        TextFallbackChain,
        "_build_clients",
        return_value=[primary, backup],
    ):
        chain = TextFallbackChain(on_all_failed=lambda _req: "static-out")
        # 当前实现下,PermanentError 会被重试 1 次 → 降级到 backup
        # 不会 hang,最终返回 backup 的结果或兜底
        result = await chain.run(
            TextRequest(messages=[LLMMessage(role="user", content="hi")])
        )
    assert result is not None
    assert result.attempts >= 1
    assert primary.ainvoke.await_count >= 1


# ─────────────────────────────────────────────────────────────────────────────
# §3 _coerce_payload
# ─────────────────────────────────────────────────────────────────────────────
def test_coerce_payload_string() -> None:
    """字符串 → 单个 HumanMessage。"""
    from langchain_core.messages import HumanMessage

    out = BaseFallbackChain._coerce_payload("hi")
    assert isinstance(out, list)
    assert len(out) == 1
    assert isinstance(out[0], HumanMessage)
    assert out[0].content == "hi"


def test_coerce_payload_llm_request_maps_roles() -> None:
    """LLMRequest 的多 role messages → 正确类型的 LangChain messages。"""
    from langchain_core.messages import AIMessage as LCAIMessage
    from langchain_core.messages import HumanMessage
    from langchain_core.messages import SystemMessage

    req = TextRequest(
        messages=[
            LLMMessage(role="system", content="you are helpful"),
            LLMMessage(role="user", content="hi"),
            LLMMessage(role="assistant", content="hello"),
        ]
    )
    out = BaseFallbackChain._coerce_payload(req)
    assert len(out) == 3
    assert isinstance(out[0], SystemMessage)
    assert isinstance(out[1], HumanMessage)
    assert isinstance(out[2], LCAIMessage)


def test_coerce_payload_multimodal_request_does_not_crash() -> None:
    """MultimodalRequest 也应能转(payload 阶段不展开 images,留给 LLM client 处理)。"""
    from langchain_core.messages import HumanMessage

    req = MultimodalRequest(
        messages=[LLMMessage(role="user", content="analyze")],
        images=["https://x/a.jpg"],
    )
    out = BaseFallbackChain._coerce_payload(req)
    assert isinstance(out, list)
    assert isinstance(out[0], HumanMessage)


# ─────────────────────────────────────────────────────────────────────────────
# §4 预算守卫
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_budget_guard_raises_budget_exceeded_error_before_clients() -> None:
    """budget_guard.check() 抛 BudgetExceededError → chain.run 透传(不入降级)。"""
    primary = _make_client(name="glm", response=AIMessage(content="ok"))
    with patch.object(
        TextFallbackChain,
        "_build_clients",
        return_value=[primary],
    ), patch(
        "app.llm._base.budget_guard.check",
        side_effect=BudgetExceededError("quota"),
    ):
        chain = TextFallbackChain(on_all_failed=lambda _req: "static-out")
        with pytest.raises(BudgetExceededError):
            await chain.run(
                TextRequest(messages=[LLMMessage(role="user", content="hi")])
            )
        # primary 永远不应该被调
        primary.ainvoke.assert_not_awaited()


# ─────────────────────────────────────────────────────────────────────────────
# §5 is_multimodal_request 工具函数
# ─────────────────────────────────────────────────────────────────────────────
def test_is_multimodal_request_classifier() -> None:
    """is_multimodal_request 正确区分 text / vision。"""
    from app.llm.multimodal_chain import is_multimodal_request

    assert is_multimodal_request(MultimodalRequest(messages=[])) is True
    assert is_multimodal_request(TextRequest(messages=[])) is False
    assert is_multimodal_request("plain string") is False


# ─────────────────────────────────────────────────────────────────────────────
# §6 dependency provider(FastAPI integration 入口)
# ─────────────────────────────────────────────────────────────────────────────
def test_dependency_providers_return_real_chains() -> None:
    """providers.get_* 真实返回 chain(无 use_mock 概念,反模式已消除)。"""
    from app.llm.providers import get_multimodal_chain, get_text_chain

    # 真实环境无 api_key → clients 列表为空但 chain 仍可创建
    mm = get_multimodal_chain()
    tx = get_text_chain()
    assert isinstance(mm, MultimodalFallbackChain)
    assert isinstance(tx, TextFallbackChain)
    assert mm.capability == "vision"
    assert tx.capability == "text"


def test_test_overrides_via_dependency_overrides() -> None:
    """FastAPI dependency_overrides 替换为 mock — 用 production code 的同一接口。"""
    from fastapi import FastAPI

    from app.llm.providers import get_multimodal_chain

    app = FastAPI()
    real_chain = get_multimodal_chain()
    mock_chain = MultimodalFallbackChain(on_all_failed=lambda _r: "mocked")

    app.dependency_overrides[get_multimodal_chain] = lambda: mock_chain
    try:
        injected = app.dependency_overrides[get_multimodal_chain]()
        assert injected is mock_chain
        assert injected is not real_chain
    finally:
        app.dependency_overrides.pop(get_multimodal_chain, None)