"""app.llm — LLM 4 级降级链（Sprint 0 骨架）。

真源：``.env`` §LLM 主备 + ``docs/spec/facts-anchor.md`` §9 + ADR-0003

降级链：Doubao Seedream → Qwen VL → DeepSeek VL → GLM（全部通过 langchain ``init_chat_model`` 初始化）
"""

from app.llm.budget import (
    BudgetExceededError,
    BudgetGuard,
    MonthlyBudgetExceededError,
    budget_guard,
)
from app.llm.client import (
    LLMClient,
    LLMMessage,
    LLMRequest,
    LLMResponse,
)
from app.llm.fallback_chain import FallbackChain, FallbackResult
from app.llm.mock_doubles import MockDoubles, MockLLMClient

__all__ = [
    "BudgetExceededError",
    "BudgetGuard",
    "FallbackChain",
    "FallbackResult",
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "MockDoubles",
    "MockLLMClient",
    "MonthlyBudgetExceededError",
    "budget_guard",
]
