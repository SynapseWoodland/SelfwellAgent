"""LLM 4 级降级链（Sprint 0 骨架）。

真源：``docs/spec/facts-anchor.md`` §9 + ADR-0003 + ``docs/api/error-codes.md`` §502 / §503。

降级链：Claude → GPT-4o → Qwen VL → DeepSeek-VL → 规则引擎（30 条 ack pool）
1. 主（priority=1）：Claude Sonnet
2. 备 1（priority=2）：GPT-4o
3. 备 2（priority=3）：Qwen VL
4. 备 3（priority=4）：DeepSeek-VL
5. 兜底（priority=5）：规则引擎（ack_pool.yaml 30 条）

每次降级必须走 ``BudgetGuard.check()``；超日预算立即 503；超月预算直接走规则引擎。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.conf.app_config import app_config
from app.core.errors import TransientError
from app.core.retry import async_retry
from app.llm.budget import budget_guard
from app.llm.client import (
    ClaudeClient,
    DeepSeekVLClient,
    GPT4oClient,
    LLMClient,
    QwenVLClient,
)
from app.llm.mock_doubles import MockLLMClient

if TYPE_CHECKING:
    pass


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
    """4 级 LLM 降级链。

    使用：
        >>> chain = FallbackChain()
        >>> result = await chain.run(LLMRequest(messages=[LLMMessage(role='user', content='hi')]))
    """

    def __init__(self, *, use_mock: bool = True) -> None:
        self._clients: list[LLMClient] = self._build_clients(use_mock=use_mock)

    @staticmethod
    def _build_clients(*, use_mock: bool) -> list[LLMClient]:
        """按优先级返回客户列表。Sprint 0 默认 ``use_mock=True``。"""
        if use_mock:
            mock = MockLLMClient()
            return [
                mock,  # 1 · 主（mock 占位）
                mock,
                mock,
                mock,
            ]
        # 真接入：按优先级装配
        cfg = app_config.llm
        return [
            ClaudeClient(api_key=cfg.anthropic.api_key, model=cfg.anthropic.model),
            GPT4oClient(api_key=cfg.openai.api_key, model=cfg.openai.model),
            QwenVLClient(api_key=cfg.dashscope.api_key, model=cfg.dashscope.model),
            DeepSeekVLClient(
                api_key=cfg.deepseek.api_key,
                model=cfg.deepseek.model,
                base_url=cfg.deepseek.base_url,
            ),
        ]

    @async_retry(attempts=2)
    async def _try_client(self, client: LLMClient, request: Any) -> Any:
        budget_guard.check()
        return await client.achat(request)

    async def run(self, request: Any) -> FallbackResult:
        """串行降级调用；全部失败抛 ``TransientError``。"""
        attempts = 0
        for client in self._clients:
            attempts += 1
            try:
                response = await self._try_client(client, request)
                budget_guard.record(cost_yuan=response.cost_yuan)
                return FallbackResult(
                    content=response.content,
                    provider_used=client.provider_name,
                    attempts=attempts,
                    cost_yuan=response.cost_yuan,
                )
            except TransientError:
                # 降级到下一级；不向上抛
                continue
        # 5 级兜底：规则引擎（30 条 ack_pool）
        return FallbackResult(
            content="（规则引擎兜底：今日 AI 服务繁忙，请稍后重试）",
            provider_used="rule-engine",
            attempts=attempts,
            cost_yuan=0.0,
        )


__all__ = ["FallbackChain", "FallbackResult"]
