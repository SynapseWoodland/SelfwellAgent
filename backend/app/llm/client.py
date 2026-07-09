"""LLM Pydantic schema（精简版）。

保留：LLMMessage + MultimodalRequest + TextRequest。
其他全部移至 app/llm/__init__.py（直接 init_chat_model 单实例）。
"""

from __future__ import annotations

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


__all__ = [
    "LLMMessage",
    "LLMRequest",
    "MultimodalRequest",
    "TextRequest",
]
