"""app.llm — LLM 双链架构(Sprint D 重构)。

Sprint D 之前:单体 ``FallbackChain`` 混用 vision / text 4 级,导致
照片分析走到第 4 级(GLM 纯文本)必然失败。

Sprint D 重构:拆为两条独立链
- :class:`MultimodalFallbackChain`(vision):Doubao Seedream → Qwen VL
- :class:`TextFallbackChain`(text):GLM → DeepSeek

降级链调用方通过 FastAPI ``dependency_overrides`` 注入 mock(mock 本身
已迁移到 ``tests/doubles/mock_llm.py``,**不**在此处导出),生产代码
完全不知道 mock 存在(根治 Sprint 0 ``use_mock`` 反模式)。
"""

from app.llm._base import BaseFallbackChain, FallbackResult
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
    MultimodalRequest,
    TextRequest,
)
from app.llm.multimodal_chain import MultimodalFallbackChain, is_multimodal_request
from app.llm.text_chain import TextFallbackChain

__all__ = [
    "BaseFallbackChain",
    "BudgetExceededError",
    "BudgetGuard",
    "FallbackResult",
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "MonthlyBudgetExceededError",
    "MultimodalFallbackChain",
    "MultimodalRequest",
    "TextFallbackChain",
    "TextRequest",
    "budget_guard",
    "is_multimodal_request",
]