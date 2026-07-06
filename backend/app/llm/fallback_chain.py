"""LLM 4 级降级链（Sprint 0 骨架）。

真源：``.env`` §LLM 主备 + ``docs/spec/facts-anchor.md`` §9 + ADR-0003。

降级链（全部 OpenAI-compatible，通过 langchain ``init_chat_model`` 统一初始化）：
    1. 主多模态（Doubao Seedream）：MULTI_*（vision / image generation）
    2. 备多模态（Qwen VL）：BACKUP_MULTI_*（vision / image generation）
    3. 备文本（DeepSeek VL）：BACKUP_*（text）
    4. 主文本（GLM）：API_KEY / MODEL / BASE_URL（text only）

每次降级必须走 ``BudgetGuard.check()``；超日预算立即 503；超月预算直接走规则引擎。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config
from app.core.errors import TransientError
from app.core.retry import async_retry
from app.llm.budget import budget_guard
from app.llm.mock_doubles import MockLLMClient

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


@dataclass(slots=True)
class FallbackResult:
    """降级链最终结果。"""

    content: str
    provider_used: str
    attempts: int
    cost_yuan: float


# ─────────────────────────────────────────────────────────────────────────────
# §一 降级链（按优先级排序）
# ─────────────────────────────────────────────────────────────────────────────
class FallbackChain:
    """4 级 LLM 降级链（全部 OpenAI-compatible）。

    使用：
        >>> chain = FallbackChain()
        >>> result = await chain.run(LLMRequest(messages=[LLMMessage(role='user', content='hi')]))
    """

    def __init__(self, *, use_mock: bool = True) -> None:
        self._clients: list[BaseChatModel] = self._build_clients(use_mock=use_mock)

    @staticmethod
    def _build_clients(*, use_mock: bool) -> list[BaseChatModel]:
        """按优先级返回 LangChain chat model 列表。Sprint 0 默认 ``use_mock=True``。"""
        if use_mock:
            return [MockLLMClient() for _ in range(4)]
        cfg = app_config.llm
        return [
            # 1 · 主多模态（Doubao Seedream）
            init_chat_model(
                model=cfg.multi_model,
                model_provider="openai",
                base_url=cfg.multi_base_url,
                api_key=cfg.multi_api_key,
                temperature=cfg.temperature,
            ),
            # 2 · 备多模态（Qwen VL）
            init_chat_model(
                model=cfg.backup_multi_model,
                model_provider="openai",
                base_url=cfg.multi_base_url,  # Qwen VL 同用 Ark base_url
                api_key=cfg.backup_multi_api_key,
                temperature=cfg.temperature,
            ),
            # 3 · 备文本（DeepSeek VL）
            init_chat_model(
                model=cfg.backup_model,
                model_provider="openai",
                base_url=cfg.backup_base_url,
                api_key=cfg.backup_api_key,
                temperature=cfg.temperature,
            ),
            # 4 · 主文本（GLM，Ark）
            init_chat_model(
                model=cfg.model,
                model_provider="openai",
                base_url=cfg.base_url,
                api_key=cfg.api_key,
                temperature=cfg.temperature,
            ),
        ]

    @async_retry(attempts=2)
    async def _try_client(self, client: BaseChatModel, request: Any) -> Any:
        budget_guard.check()
        return await client.ainvoke(request)  # type: ignore[attr-defined]

    async def run(self, request: Any) -> FallbackResult:
        """串行降级调用；全部失败抛 ``TransientError``。"""
        attempts = 0
        for client in self._clients:
            attempts += 1
            try:
                response = await self._try_client(client, request)
                # LangChain 返回 BaseMessage，取 .content
                content = response.content if hasattr(response, "content") else str(response)
                return FallbackResult(
                    content=content,
                    provider_used=getattr(client, "model", str(client)),
                    attempts=attempts,
                    cost_yuan=0.0,
                )
            except TransientError:
                continue
        return FallbackResult(
            content="（规则引擎兜底：今日 AI 服务繁忙，请稍后重试）",
            provider_used="rule-engine",
            attempts=attempts,
            cost_yuan=0.0,
        )


__all__ = ["FallbackChain", "FallbackResult"]
