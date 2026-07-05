"""app.llm — LLM 4 级降级链（Sprint 0 骨架）。

真源：``docs/spec/facts-anchor.md`` §9 + ADR-0003
"""

from app.llm.budget import (
    BudgetExceededError,
    BudgetGuard,
    MonthlyBudgetExceededError,
    budget_guard,
)
from app.llm.client import (
    ClaudeClient,
    DeepSeekVLClient,
    GPT4oClient,
    LLMClient,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    QwenVLClient,
)
from app.llm.fallback_chain import FallbackChain, FallbackResult
from app.llm.mock_doubles import MockDoubles, MockLLMClient

__all__ = [
    "BudgetExceededError",
    "BudgetGuard",
    "ClaudeClient",
    "DeepSeekVLClient",
    "FallbackChain",
    "FallbackResult",
    "GPT4oClient",
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "MockDoubles",
    "MockLLMClient",
    "MonthlyBudgetExceededError",
    "QwenVLClient",
    "budget_guard",
]
