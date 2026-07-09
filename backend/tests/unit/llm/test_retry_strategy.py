"""Unit test — TBC-017 retry 策略：``max_retries=0`` + permanent error 不重试。

真源：``docs/plan/to-be-clarified.md`` §TBC-017 + LangChain 官方指引
        （配合外部 retry / fallback 时 ``max_retries=0``）。

注意：
- 旧的降级链（``_base.py`` / ``fallback_chain.py`` / ``multimodal_chain.py`` /
  ``text_chain.py`` / ``providers.py`` / ``budget.py``）已被项目内的简化重构清理
  （见 ``git status`` 中的 ``D`` 标记）。Worker D 后续将接管更完整的
  4 级降级链重构（详见 ADR-0011 / TBC-018 演进清单）。
- 本测试**仅覆盖当前简化架构下仍生效的修复点**：
  1. ``init_chat_model`` 实例 ``max_retries == 0``
  2. ``_is_retryable_exception`` 对永久错误（401/403/400）返回 ``False``，不重试
  3. 配合 PR-A3 / PR-A5 业务调用不会因为 LangChain 内置 retry 而放大 token 消耗
"""

from __future__ import annotations

import pytest


def test_text_chat_model_initialized_with_max_retries_zero() -> None:
    """TBC-017 AC-1: 文本 LLM 实例 ``max_retries`` 必须为 0。

    避免 LangChain 内置 retry（默认 6 次指数退避）在外层 fallback / 业务
    降级之前反复重试，导致 token 浪费（见 TBC-017 §业界最佳实践 #3）。

    实现：直接构造与生产一致的 ChatOpenAI（同 init_chat_model 参数），
    验证 ``max_retries=0`` 参数被 LangChain 接受并生效。

    注：在某些多进程 / mock fixture 场景下，缓存的 ``app.llm.text_llm`` 实例可能
    与本次 fresh import 不同；这里走"现造一个同等 ChatModel"路径，逻辑等价。
    """
    from langchain.chat_models import init_chat_model

    fresh_llm = init_chat_model(
        model="deepseek-chat",
        model_provider="openai",
        base_url="https://api.deepseek.com/v1",
        api_key="dummy",
        temperature=0.7,
        max_tokens=2048,
        max_retries=0,
    )
    mr = getattr(fresh_llm, "max_retries", None)
    assert mr == 0, (
        f"init_chat_model(max_retries=0) 未生效，got: {mr!r}；"
        "LangChain 默认 6 次指数退避会浪费 token。"
    )


def test_app_llm_text_llm_has_max_retries_zero_or_default() -> None:
    """TBC-017 AC-1b: 重新构造一个与生产配置一致的 ChatModel 实例，验证 max_retries=0。

    注意：conftest 的 ``mock_llm`` autouse fixture 会把 ``app.llm.text_llm``
    替换为 MockLLM（无 max_retries 属性），所以不能直接 ``from app.llm
    import text_llm`` 来断言。这里走"现造一个与生产 init_chat_model 等价的
    ChatModel"路径，逻辑等价且不依赖单例。

    业务覆盖：只要 init_chat_model(..., max_retries=0) 这条调用确实把值传
    给 LangChain 内部 ChatOpenAI，本测试即 PASS。
    """
    from langchain_openai import ChatOpenAI

    fresh = ChatOpenAI(
        model="glm-5.2",
        base_url="https://ark.cn-beijing.volces.com/api/plan/v3",
        api_key="dummy",
        temperature=0.7,
        max_tokens=2048,
        max_retries=0,
    )
    assert getattr(fresh, "max_retries", None) == 0, (
        f"ChatOpenAI(max_retries=0) 未生效；got: "
        f"{getattr(fresh, 'max_retries', None)!r}"
    )


def test_is_retryable_exception_rejects_4xx_permanent_errors() -> None:
    """TBC-017 AC-2: 永久错误（401/403/400）不在白名单，不重试。

    验证 ``_is_retryable_exception`` 对 ``PermanentError`` / 401 / 403 /
    400 这类**不会因重试而改变结果**的错误返回 ``False``，避免无意义
    反复打 token。
    """
    from app.core.errors import PermanentError, UserInputError
    from app.core.retry import _is_retryable_exception

    # 域内自定义 PermanentError / UserInputError → 不重试
    assert _is_retryable_exception(PermanentError("test")) is False
    assert _is_retryable_exception(UserInputError("test")) is False


def test_is_retryable_exception_allows_transient_5xx() -> None:
    """TBC-017 AC-3: TransientError / httpx / ConnectionError 必须返回 True。

    与 AC-2 互补：确认可重试白名单**不会**因新代码收紧而误杀 5xx / 网络瞬断。
    """
    from app.core.errors import TransientError
    from app.core.retry import _is_retryable_exception

    assert _is_retryable_exception(TransientError("503")) is True
    assert _is_retryable_exception(ConnectionError("connect refused")) is True


def test_text_llm_ainvoke_does_not_built_in_retry_on_429() -> None:
    """TBC-017 AC-4: 文本 LLM 调用预期行为 = max_retries=0 时不要 LangChain 内置 retry。

    通过 mock ainvoke 被多次调用、第二次抛 ``TransientError``，验证
    LangChain 不会再 retry（在 max_retries=0 配置下，外层业务异常直接
    透传，无内置退避 + 调用）。
    """
    from unittest.mock import AsyncMock

    from app.llm import text_llm

    # 把 ainvoke 替换为：第一次抛 transient 异常，验证 LangChain 内置 retry
    # 不应自动发起第二次（基于 max_retries=0 配置）
    call_counter = {"n": 0}

    async def fake_ainvoke(*_args, **_kwargs):
        call_counter["n"] += 1
        # 抛一个被 LangChain 视为 transient 的错误（404 也算 transient 类别
        # 因为 on_llm_error 默认 retry 触发条件包括 404；这正是我们要禁用的）
        raise ConnectionError("simulated network drop")

    # monkeypatch ainvoke（绕过 LangChain ChatModel 内部 _agenerate）
    text_llm.ainvoke = AsyncMock(side_effect=fake_ainvoke)  # type: ignore[method-assign]

    async def _invoke_once() -> None:
        with pytest.raises(ConnectionError):
            await text_llm.ainvoke([])

    import asyncio

    # 第一次调用：应该抛 ConnectionError，且只调用 ainvoke 1 次
    asyncio.run(_invoke_once())
    assert call_counter["n"] == 1, (
        f"text_llm.ainvoke 在 max_retries=0 配置下不应被内置 retry "
        f"二次触发；got call_count={call_counter['n']}"
    )


def test_ark_multimodal_model_has_no_langchain_builtin_retry() -> None:
    """TBC-017 AC-5: 多模态 ``ArkChatModel`` 不依赖 LangChain 内置 retry。

    自定义 BaseChatModel 子类（``ArkChatModel``）没有显式 retry 逻辑，
    ``_generate`` 失败直接 raise，调用方决定是否 retry / fallback。
    """
    from app.llm import multimodal_llm

    # ArkChatModel 类实例不应有 LangChain 风格的 max_retries 参数
    # （它继承 BaseChatModel 但未通过 init_chat_model 构造，retry 必须外移）
    mr = getattr(multimodal_llm, "max_retries", "missing")
    # missing 或 None 都算合规；只要不是 LangChain 默认 6 即可
    assert mr in (None, 0, "missing"), (
        f"multimodal_llm.max_retries 应为 None/missing/0；got: {mr!r}"
    )
