"""LLM Pydantic Schema（Sprint 0 骨架）。

真源：``.env`` §LLM 主备 + ``docs/spec/facts-anchor.md`` §9 + ADR-0003。

约定：
1. **Sprint 0 使用 MockLLMClient**，不调真实模型
2. 真实模型通过 Sprint 2+ 接入，统一走 ``langchain.chat_models.init_chat_model``
3. 4 级降级链：Doubao Seedream → Qwen VL → DeepSeek VL → GLM
4. input/output schema 严格 Pydantic v2（``LLMRequest`` / ``LLMResponse``）
5. 任何 LLM 调用必须带 ``trace_id`` / ``request_id`` / ``user_id_pseudo`` 上下文
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# §一 Pydantic v2 Schema（跨 4 级降级链统一入参 / 出参）
# ─────────────────────────────────────────────────────────────────────────────
class LLMMessage(BaseModel):
    """单条聊天消息。"""

    role: str = Field(..., description="user / assistant / system")
    content: str = Field(..., min_length=0, max_length=4000)


class LLMRequest(BaseModel):
    """LLM 统一入参。"""

    messages: list[LLMMessage] = Field(default_factory=list)
    images: list[str] = Field(
        default_factory=list,
        description="Image URLs or base64 (for multimodal diagnosis / vision tasks)",
    )
    model: str | None = Field(default=None, description="Override default model")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """LLM 统一出参。"""

    content: str
    model: str
    latency_ms: int
    token_count: int = 0
    cost_yuan: float = 0.0
    finish_reason: str = "stop"
    raw: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# §二 LLMClient 抽象基类（仅用于 mock 场景，Sprint 0）
# ─────────────────────────────────────────────────────────────────────────────
class LLMClient(ABC):
    """LLM 客户端抽象基类（仅 Sprint 0 mock 使用）。

    Sprint 2+ 真实接入统一走 ``langchain.chat_models.init_chat_model``，
    不再使用此类。
    """

    provider_name: str = "mock"

    @abstractmethod
    async def achat(self, request: LLMRequest) -> LLMResponse:
        """异步 chat 调用（mock 实现）。"""


__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
]
