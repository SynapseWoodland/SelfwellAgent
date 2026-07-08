"""LLM Pydantic schema.

生产路径按能力拆分为两类请求：
- ``MultimodalRequest``：照片智能分析等 vision 场景
- ``TextRequest``：智能管家聊天 / 调理常识等纯文本场景

保留 ``LLMRequest.images`` 是为了兼容现有 cassette 与迁移期代码。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """单条聊天消息。"""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="system / user / assistant"
    )
    content: str = Field(..., min_length=0, max_length=4000)


class LLMRequest(BaseModel):
    """LLM 统一入参基类。"""

    messages: list[LLMMessage] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list, description="Image URLs or base64 data URLs")
    model: str | None = Field(default=None, description="Override default model")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    metadata: dict[str, Any] = Field(default_factory=dict)
    capability: Literal["text", "vision"] = "text"


class MultimodalRequest(LLMRequest):
    """多模态请求，必须走 vision-capable 模型。"""

    capability: Literal["vision"] = "vision"


class TextRequest(LLMRequest):
    """纯文本请求，必须走 text 模型。"""

    capability: Literal["text"] = "text"
    images: list[str] = Field(default_factory=list, max_length=0)


class LLMResponse(BaseModel):
    """LLM 统一出参。"""

    content: str
    model: str
    latency_ms: int
    token_count: int = 0
    cost_yuan: float = 0.0
    finish_reason: str = "stop"
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMClient(ABC):
    """LLM 客户端抽象基类，主要用于测试替身。"""

    provider_name: str = "mock"

    @abstractmethod
    async def achat(self, request: LLMRequest) -> LLMResponse:
        """异步 chat 调用。"""


__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "MultimodalRequest",
    "TextRequest",
]
